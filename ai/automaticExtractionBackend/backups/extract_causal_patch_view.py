"""
 @file: extract_causal_patch_view.py
 @Time    : 2025/4/10
 @Author  : Peinuan qin
 """
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

#
#
# CAUSAL_PROMPT = """
# Step 3: causal-relation extraction
# [Instruction]
# Analyze the given sentence and the two identified entities with their constructs. Determine if there is a meaningful causal relationship between these entities based on the text evidence. Determine if there is a causal relationship between these entities based on explicit causal markers (e.g., because, since, as, therefore) or implicit semantic relationships.
#
# A causal relationship exists when one entity (cause) leads to, results in, or influences another entity (effect).
#
# IMPORTANT:
# 1. Focus primarily on implicit semantic relationships rather than just explicit causal markers. Most causal relationships will NOT be indicated by words like "because" or "therefore" but must be inferred from the meaning and context of the sentence.
# 2. The relationship field in the output must always be "lead to" - your task is to correctly identify which entity is the cause (comes before "lead to") and which is the effect (comes after "lead to").
# 3. Pay careful attention to the direction of causality - determine which entity leads to or influences the other, not the reverse.
#
# [Input Format]
# - Sentence: The complete sentence from a qualitative data interview transcript
# - Entity 1: The first entity with its construct type in parentheses
# - Entity 2: The second entity with its construct type in parentheses
#
# [Output Format]
# Return the results in JSON format:
#
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
# [Example 1]
# Sentence: "No, I would not feel angry, I would feel concerned and try to talk to them to calm them down. It is out of the ordinary behaviour for them, I do not like seeing people angry or arguments so I would try and defuse the situation."
# Entity 1: "would not feel angry" (emotional response)
# Entity 2: "try to talk to them" (behavioral intention)
#
# Output:
# {
#   "causal_relationship": {
#     "cause": "would not feel angry",
#     "relationship": "lead to",
#     "effect": "try to talk to them"
#   }
# }
#
# [Example 2]
# Sentence: "No, I would not feel angry, I would feel concerned and try to talk to them to calm them down. It is out of the ordinary behaviour for them, I do not like seeing people angry or arguments so I would try and defuse the situation."
# Entity 1: "I do not like seeing people angry" (belief)
# Entity 2: "I do not like arguments" (belief)
#
# Output:
# {
#   "causal_relationship": "none"
# }
#
# [Input]
# """




CAUSAL_PROMPT = """
Step 3: causal-relation extraction
[Instruction]
Analyze the given sentence and the two identified entities with their constructs. Determine if there is a meaningful causal relationship between these entities based on the text evidence. Determine if there is a causal relationship between these entities based on explicit causal markers (e.g., because, since, as, therefore) or implicit semantic relationships.

A causal relationship exists when one entity (cause) leads to, results in, or influences another entity (effect).

IMPORTANT: 
1. Consider both explicit causal markers (like "because," "therefore," "since," "as a result") AND implicit causal relationships. While many causal relationships are explicitly indicated, others might be inferred from the meaning and context of the sentence. Both types are equally valid for this task.
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
        llm = ChatOpenAI(model="gpt-4o", temperature=0)

        # 拿到 user 的所有 sentences 并提前查询每个 sentence 的 entities，并且每个 entity 的 construct
        sentences = Sentence.objects.filter(user=user).prefetch_related("entities", "entities__construct")

        tasks = []
        seen_pairs = set()

        for sentence in sentences:
            entities = list(sentence.entities.all())

            # 如果目前的 sentence 能够获得的 entity 数量小于 2 则直接忽略即可，并不需要进一步提取
            if len(entities) < 2:
                continue

            # 如果多于 2 个，则可以通过 combination 的方式任意组合
            for e1, e2 in combinations(entities, 2):
                # 对于每个 entity，如果他已经有了 canonical_entity 就代表是已经消歧过的 entity，我们需要拿到他真正的指向的 entity
                # 如果是尚未消歧的 entity，就直接使用本体就好
                canon1 = e1.canonical_entity or e1
                canon2 = e2.canonical_entity or e2
                # 在不考虑顺序的情况下，唯一标识一对 entity 的组合。
                """
                canon1.id 和 canon2.id 取出两个 entity 的 canonical id；
                sorted([...]) 会让 (A, B) 和 (B, A) 始终变成一样的顺序；
                tuple(...) 把它变成一个不可变键（可以放进 set 里判断唯一性）；
                """
                pair_key = tuple(sorted([canon1.id, canon2.id]))
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

        """
        开始抽取 casual relationship
        """
        created = []
        for r in results:
            rel = r["result"].get("causal_relationship")
            # 如果某个 tuple 规定的内容中没有抽到任何东西；忽略
            if rel == "none" or not isinstance(rel, dict):
                continue

            # 抽到了，就分别存到 cause, effect 中
            cause = rel.get("cause")
            effect = rel.get("effect")

            # ✳️ Canonical 实体
            e1 = r["e1"].canonical_entity or r["e1"]
            e2 = r["e2"].canonical_entity or r["e2"]

            # ✳️ 排除 cause == effect（无论是 name 还是 id）
            if cause == effect or e1.id == e2.id:
                continue

            # ✳️ 检查匹配方向
            if cause == r["e1"].name and effect == r["e2"].name:
                start, end = e1, e2
            elif cause == r["e2"].name and effect == r["e1"].name:
                start, end = e2, e1
            else:
                continue

            # ✳️ 避免重复 triple（同一句话中）
            if Triple.objects.filter(user=user, sentence=r["sentence"], entity_cause=start, entity_effect=end).exists():
                continue

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

        # 🔁 冲突检测 & 解决
        causal_map = {}
        conflicts = []

        triples = Triple.objects.filter(user=user).select_related("entity_cause", "entity_effect", "sentence")
        for triple in triples:
            key = (triple.entity_cause.id, triple.entity_effect.id)
            causal_map[key] = triple

        for (a, b) in list(causal_map.keys()):
            if (b, a) in causal_map:
                conflicts.append((causal_map[(a, b)], causal_map[(b, a)]))

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
                return (t1, t2, result.get("preferred_relationship"))
            except Exception as e:
                print(f"❌ Conflict resolution failed: {e}")
                return (t1, t2, None)

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

        return JsonResponse({"created_triples": created}, status=200)

    except SystemUser.DoesNotExist:
        return JsonResponse({"error": "User not found"}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
