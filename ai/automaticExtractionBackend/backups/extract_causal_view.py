import json
from itertools import combinations
from concurrent.futures import ThreadPoolExecutor, as_completed

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from langchain_core.output_parsers import JsonOutputParser

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from automaticExtractionBackend.models import SystemUser, Sentence, Triple
parser = JsonOutputParser()


# CAUSAL_PROMPT = """
# Analyze the given sentence and the two identified entities with their constructs. Determine if there is a causal relationship between these entities based on explicit causal markers (e.g., because, since, as, therefore) or implicit semantic relationships.
#
# A causal relationship exists when one entity (cause) leads to, results in, or influences another entity (effect).
#
# IMPORTANT: Focus primarily on implicit semantic relationships rather than just explicit causal markers. Most causal relationships will NOT be indicated by words like "because" or "therefore" but must be inferred from the meaning and context of the sentence.
#
# [Input Format]
# - Sentence: The complete sentence from a qualitative data interview transcript
# - Entity 1: The first entity with its construct type in parentheses
# - Entity 2: The second entity with its construct type in parentheses
#
# [Output Format]
# If a causal relationship exists:
# {
#   "causal_relationship": {
#     "cause": "entity that is the cause",
#     "relationship": "lead to",
#     "effect": "entity that is the effect"
#   }
# }
#
# If no causal relationship exists:
# {
#   "causal_relationship": "none"
# }
#
# Please note that all quotation marks should be double quotes.
# """


CAUSAL_PROMPT = """
Step 3: causal-relation extraction
[Instruction]
Analyze the given sentence and the two identified entities with their constructs. Determine if there is a meaningful causal relationship between these entities based on the text evidence. Determine if there is a causal relationship between these entities based on explicit causal markers (e.g., because, since, as, therefore) or implicit semantic relationships.

A causal relationship exists when one entity (cause) leads to, results in, or influences another entity (effect).

IMPORTANT: 
1. Focus primarily on implicit semantic relationships rather than just explicit causal markers. Most causal relationships will NOT be indicated by words like "because" or "therefore" but must be inferred from the meaning and context of the sentence.
2. The relationship field in the output must always be "lead to" - your task is to correctly identify which entity is the cause (comes before "lead to") and which is the effect (comes after "lead to").
3. Pay careful attention to the direction of causality - determine which entity leads to or influences the other, not the reverse.

[Input Format]
- Sentence: The complete sentence from a qualitative data interview transcript
- Entity 1: The first entity with its construct type in parentheses
- Entity 2: The second entity with its construct type in parentheses

[Output Format]
Return the results in JSON format:

If a causal relationship exists:
{
  "causal_relationship": {
    "cause": "entity that is the cause",
    "relationship": "lead to",
    "effect": "entity that is the effect"
  }
}

If no causal relationship exists:
{
  "causal_relationship": "none"
}

[Example 1]
Sentence: "No, I would not feel angry, I would feel concerned and try to talk to them to calm them down. It is out of the ordinary behaviour for them, I do not like seeing people angry or arguments so I would try and defuse the situation."
Entity 1: "would not feel angry" (emotional response)
Entity 2: "try to talk to them" (behavioral intention)

Output:
{
  "causal_relationship": {
    "cause": "would not feel angry",
    "relationship": "lead to",
    "effect": "try to talk to them"
  }
}

[Example 2]
Sentence: "No, I would not feel angry, I would feel concerned and try to talk to them to calm them down. It is out of the ordinary behaviour for them, I do not like seeing people angry or arguments so I would try and defuse the situation."
Entity 1: "I do not like seeing people angry" (belief)
Entity 2: "I do not like arguments" (belief)

Output:
{
  "causal_relationship": "none"
}

[Input]
"""


def analyze_pair(llm, sentence, e1, e2):
    construct1 = e1.construct.name if e1.construct else "unknown"
    construct2 = e2.construct.name if e2.construct else "unknown"

    prompt = f"""
- Sentence: {sentence.text}
- Entity 1: {e1.name} ({construct1})
- Entity 2: {e2.name} ({construct2})
"""
    print("prompt:", prompt)

    messages = [
        SystemMessage(content=CAUSAL_PROMPT),
        HumanMessage(content=prompt),
    ]

    try:
        response = llm.invoke(messages)
        result = parser.parse(response.content)  # ✅ 使用 parser.parse 强制返回为 dict
        # result = json.loads(response.content)
        # result = response
        # print("result:", response)
        print("result:", result)

        return {
            "sentence": sentence,
            "e1": e1,
            "e2": e2,
            "result": result
        }
    except Exception as e:
        print(f"❌ Error analyzing pair ({e1.name}, {e2.name}): {e}")
        return None


@csrf_exempt
def extract_causal_relations(request):
    if request.method != "POST":
        return JsonResponse({"error": "Only POST method allowed"}, status=405)

    try:
        data = json.loads(request.body)
        user_id = data.get("user_id")
        if not user_id:
            return JsonResponse({"error": "Missing user_id"}, status=400)

        user = SystemUser.objects.get(pk=user_id)
        # llm = ChatOpenAI(model="gpt-4o", temperature=0, response_format="json")  # 强制 JSON 输出
        llm = ChatOpenAI(model="gpt-4o", temperature=0)

        sentences = Sentence.objects.filter(user=user).prefetch_related("entities", "entities__construct")

        # tasks = []
        # for sentence in sentences:
        #     entities = list(sentence.entities.all())
        #     if len(entities) < 2:
        #         continue
        #     for e1, e2 in combinations(entities, 2):
        #         tasks.append((sentence, e1, e2))

        """
        下述操作用来保证 A, B 如果已经给 LLM 判断过了，就不需要再将 B, A 判断一次了
        """
        tasks = []
        seen_pairs = set()  # 用于记录已处理的实体对（无序）

        for sentence in sentences:
            entities = list(sentence.entities.all())
            if len(entities) < 2:
                continue
            for e1, e2 in combinations(entities, 2):
                # 用 ID 构造一个无序对 key，这样 (A, B) 和 (B, A) 是等价的
                pair_key = tuple(sorted([e1.id, e2.id]))
                if pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)
                tasks.append((sentence, e1, e2))

        results = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_task = {
                executor.submit(analyze_pair, llm, s, e1, e2): (s, e1, e2)
                for s, e1, e2 in tasks
            }
            for future in as_completed(future_to_task):
                result = future.result()
                if result:
                    results.append(result)

        created = []
        for r in results:
            rel = r["result"].get("causal_relationship")
            if rel == "none" or not isinstance(rel, dict):
                continue

            cause = rel.get("cause")
            effect = rel.get("effect")

            if cause == r["e1"].name and effect == r["e2"].name:
                start, end = r["e1"], r["e2"]
            elif cause == r["e2"].name and effect == r["e1"].name:
                start, end = r["e2"], r["e1"]
            else:
                continue

            # triple, created_flag = Triple.objects.get_or_create(
            #     user=user,
            #     sentence=r["sentence"],
            #     start_entity=start,
            #     end_entity=end,
            # )

            if start.id == end.id:
                continue  # 跳过 reflexive 的情况

            triple, created_flag = Triple.objects.get_or_create(
                user=user,
                sentence=r["sentence"],
                entity_cause=start,
                entity_effect=end,
            )

            if created_flag:
                created.append({
                    "sentence_id": r["sentence"].id,
                    "cause": start.name,
                    "effect": end.name
                })

        # 如果不进行成环检测就可以直接返回了
        # return JsonResponse({"created_triples": created}, status=200)

        # ============== 🔁 进行冲突检测（A→B 与 B→A） =================
        causal_map = {}
        conflicts = []

        # 获取所有用户的 triples，并构建字典
        triples = Triple.objects.filter(user=user).select_related("entity_cause", "entity_effect", "sentence")

        for triple in triples:
            key = (triple.entity_cause.id, triple.entity_effect.id)
            causal_map[key] = triple

        # 查找是否存在反向对（B→A）
        for (a, b) in list(causal_map.keys()):
            if (b, a) in causal_map:
                conflicts.append((causal_map[(a, b)], causal_map[(b, a)]))

        # 解决冲突
        CONFLICT_PROMPT = """
You are given two causal relationships extracted from the same user's qualitative data:

1. "{sentence1}" 
   Causal relationship: "{cause1}" leads to "{effect1}"

2. "{sentence2}" 
   Causal relationship: "{cause2}" leads to "{effect2}"

These relationships form a logical loop (A → B and B → A). Your task is to decide which one is more reasonable based on semantics and context.

[Output Format]
{{
  "preferred_relationship": "1"  // or "2"
}}
"""

        # def resolve_conflict(llm, t1, t2):
        #     prompt = CONFLICT_PROMPT.format(
        #         sentence1=t1.sentence.text,
        #         cause1=t1.entity_cause.name,
        #         effect1=t1.entity_effect.name,
        #         sentence2=t2.sentence.text,
        #         cause2=t2.entity_cause.name,
        #         effect2=t2.entity_effect.name,
        #     )
        #     try:
        #         response = llm.invoke([HumanMessage(content=prompt)])
        #         result = parser.parse(response.content)
        #         return result.get("preferred_relationship")
        #     except Exception as e:
        #         print(f"❌ Conflict resolution failed: {e}")
        #         return None

        def resolve_conflict_pair(t1, t2):
            prompt = CONFLICT_PROMPT.format(
                sentence1=t1.sentence.text,
                cause1=t1.entity_cause.name,
                effect1=t1.entity_effect.name,
                sentence2=t2.sentence.text,
                cause2=t2.entity_cause.name,
                effect2=t2.entity_effect.name,
            )
            try:
                response = llm.invoke([HumanMessage(content=prompt)])
                result = parser.parse(response.content)
                print("resolve conflict pair result:", result)
                return (t1, t2, result.get("preferred_relationship"))
            except Exception as e:
                print(f"❌ Conflict resolution failed: {e}")
                return (t1, t2, None)

        # for t1, t2 in conflicts:
        #     preferred = resolve_conflict(llm, t1, t2)
        #     if preferred == "1":
        #         t2.delete()
        #     elif preferred == "2":
        #         t1.delete()
        #     else:
        #         print(f"⚠️ Could not resolve causal loop between {t1.id} and {t2.id}")

        # 并发执行冲突解决
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(resolve_conflict_pair, t1, t2) for t1, t2 in conflicts]
            for future in as_completed(futures):
                t1, t2, preferred = future.result()
                if preferred == "1":
                    t2.delete()
                elif preferred == "2":
                    t1.delete()
                else:
                    print(f"⚠️ Could not resolve causal loop between {t1.id} and {t2.id}")

        # ✅ 最后返回创建的三元组
        return JsonResponse({"created_triples": created}, status=200)
        # return JsonResponse({"created_triples": created}, status=200)

    except SystemUser.DoesNotExist:
        return JsonResponse({"error": "User not found"}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
