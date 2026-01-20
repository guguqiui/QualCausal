# import asyncio
# import json
# from itertools import combinations
# from django.http import JsonResponse
# from django.views.decorators.csrf import csrf_exempt
# from django.views.decorators.http import require_http_methods
# from langchain_core.output_parsers import JsonOutputParser
# from langchain_openai import ChatOpenAI
# from langchain_core.messages import SystemMessage, HumanMessage
# from automaticExtractionBackend.models import SystemUser, Sentence, Triple



# parser = JsonOutputParser()

# CAUSAL_PROMPT = """
# [Instruction]
# Analyze the given sentence and the two identified entities with their constructs. Determine if there is a meaningful causal relationship between these entities based on the text evidence. Determine if there is a causal relationship between these entities based on explicit causal markers (e.g., because, since, as, therefore) or implicit semantic relationships.
#
# A causal relationship exists when one entity (cause) leads to, results in, or influences another entity (effect).
#
# IMPORTANT:
# 1. Consider both explicit causal markers (like "because," "therefore," "since," "as a result") AND implicit causal relationships. While many causal relationships are explicitly indicated, others might be inferred from the meaning and context of the sentence. Both types are equally valid for this task.
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

# def analyze_pair_sync(llm, sentence, e1, e2):
#     """Synchronous wrapper for the async analyze_pair function"""
#     async def _analyze_pair():
#         return await analyze_pair(llm, sentence, e1, e2)
#     return asyncio.run(_analyze_pair())
#
# async def analyze_pair(llm, sentence, e1, e2):
#     """Async function to analyze entity pairs"""
#     construct1 = e1.construct.name if e1.construct else "unknown"
#     construct2 = e2.construct.name if e2.construct else "unknown"
#
#     prompt = f"""
# - Sentence: {sentence.text}
# - Entity 1: {e1.name} ({construct1})
# - Entity 2: {e2.name} ({construct2})
# """
#     messages = [
#         SystemMessage(content=CAUSAL_PROMPT),
#         HumanMessage(content=prompt),
#     ]
#
#     try:
#         response = await llm.agenerate([messages])
#         result = parser.parse(response.generations[0][0].text)
#         return {
#             "sentence": sentence,
#             "e1": e1,
#             "e2": e2,
#             "result": result
#         }
#     except Exception as e:
#         print(f"❌ Error analyzing pair ({e1.name}, {e2.name}): {e}")
#         return None
#
# @csrf_exempt
# @require_http_methods(["POST"])
# def extract_causal_relations(request):
#     if request.method != "POST":
#         return JsonResponse({"error": "Only POST method allowed"}, status=405)
#
#     try:
#         data = json.loads(request.body)
#         user_id = data.get("user_id")
#         if not user_id:
#             return JsonResponse({"error": "Missing user_id"}, status=400)
#
#         # Get user and sentences synchronously
#         try:
#             user = SystemUser.objects.get(pk=user_id)
#             sentences = Sentence.objects.filter(user=user).prefetch_related("entities", "entities__construct")
#         except SystemUser.DoesNotExist:
#             return JsonResponse({"error": "User not found"}, status=404)
#
#         llm = ChatOpenAI(model="gpt-4o", temperature=0)
#
#         # Prepare tasks
#         tasks = []
#         seen_pairs = set()
#
#         for sentence in sentences:
#             entities = list(sentence.entities.all())
#             if len(entities) < 2:
#                 continue
#
#             for e1, e2 in combinations(entities, 2):
#                 canon1 = e1.canonical_entity or e1
#                 canon2 = e2.canonical_entity or e2
#                 pair_key = tuple(sorted([canon1.id, canon2.id]))
#                 if pair_key not in seen_pairs:
#                     seen_pairs.add(pair_key)
#                     tasks.append((sentence, e1, e2))
#
#         # Process pairs synchronously using asyncio.run
#         results = []
#         for s, e1, e2 in tasks:
#             result = analyze_pair_sync(llm, s, e1, e2)
#             if result:
#                 results.append(result)
#
#         # Process results and create triples
#         created = []
#         for r in results:
#             rel = r["result"].get("causal_relationship")
#             if rel == "none" or not isinstance(rel, dict):
#                 continue
#
#             cause = rel.get("cause")
#             effect = rel.get("effect")
#
#             e1 = r["e1"].canonical_entity or r["e1"]
#             e2 = r["e2"].canonical_entity or r["e2"]
#
#             if cause == effect or e1.id == e2.id:
#                 continue
#
#             if cause == r["e1"].name and effect == r["e2"].name:
#                 start, end = e1, e2
#             elif cause == r["e2"].name and effect == r["e1"].name:
#                 start, end = e2, e1
#             else:
#                 continue
#
#             # Check and create triple
#             if not Triple.objects.filter(
#                 user=user,
#                 sentence=r["sentence"],
#                 entity_cause=start,
#                 entity_effect=end
#             ).exists():
#                 Triple.objects.create(
#                     user=user,
#                     sentence=r["sentence"],
#                     entity_cause=start,
#                     entity_effect=end
#                 )
#                 created.append({
#                     "sentence_id": r["sentence"].id,
#                     "cause": start.name,
#                     "effect": end.name
#                 })
#
#         return JsonResponse({"created_triples": created, "count": len(created)}, status=200)
#
#     except json.JSONDecodeError:
#         return JsonResponse({"error": "Invalid JSON"}, status=400)
#     except Exception as e:
#         return JsonResponse({"error": str(e)}, status=500)




import asyncio
import json
from itertools import combinations
from concurrent.futures import ThreadPoolExecutor

from asgiref.sync import sync_to_async
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from langchain_core.output_parsers import JsonOutputParser
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from automaticExtractionBackend.models import SystemUser, Sentence, Triple

parser = JsonOutputParser()

# CAUSAL_PROMPT 保持不变...
CAUSAL_PROMPT = """
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


async def analyze_pair(llm, sentence, e1, e2):
    """Async function to analyze entity pairs"""
    construct1 = e1.construct.name if e1.construct else "unknown"
    construct2 = e2.construct.name if e2.construct else "unknown"

    prompt = f"""
- Sentence: {sentence.text}
- Entity 1: {e1.name} ({construct1})
- Entity 2: {e2.name} ({construct2})
"""
    messages = [
        SystemMessage(content=CAUSAL_PROMPT),
        HumanMessage(content=prompt),
    ]

    try:
        response = await llm.agenerate([messages])
        print("response:", response)
        result = parser.parse(response.generations[0][0].text)
        return {
            "sentence": sentence,
            "e1": e1,
            "e2": e2,
            "result": result
        }
    except Exception as e:
        print(f"❌ Error analyzing pair ({e1.name}, {e2.name}): {e}")
        return None

def analyze_pair_wrapper(args):
    """Wrapper function to run async analyze_pair in a thread"""
    llm, sentence, e1, e2 = args
    return asyncio.run(analyze_pair(llm, sentence, e1, e2))

@csrf_exempt
@require_http_methods(["POST"])
def extract_causal_relations(request):
    if request.method != "POST":
        return JsonResponse({"error": "Only POST method allowed"}, status=405)

    try:
        data = json.loads(request.body)
        user_id = data.get("user_id")
        if not user_id:
            return JsonResponse({"error": "Missing user_id"}, status=400)

        # Get user and sentences synchronously
        try:
            user = SystemUser.objects.get(pk=user_id)
            sentences = Sentence.objects.filter(user=user).prefetch_related("entities", "entities__construct")
        except SystemUser.DoesNotExist:
            return JsonResponse({"error": "User not found"}, status=404)

        llm = ChatOpenAI(model="gpt-4o", temperature=0)

        # Prepare tasks
        tasks = []
        seen_pairs = set()

        for sentence in sentences:
            entities = list(sentence.entities.all())
            if len(entities) < 2:
                continue

            for e1, e2 in combinations(entities, 2):
                canon1 = e1.canonical_entity or e1
                canon2 = e2.canonical_entity or e2
                pair_key = tuple(sorted([canon1.id, canon2.id]))
                if pair_key not in seen_pairs:
                    seen_pairs.add(pair_key)
                    tasks.append((llm, sentence, e1, e2))

        # Process pairs in parallel using ThreadPoolExecutor
        results = []
        with ThreadPoolExecutor(max_workers=30) as executor:  # 可以调整worker数量
            futures = [executor.submit(analyze_pair_wrapper, task) for task in tasks]
            for future in futures:
                try:
                    result = future.result()
                    if result:
                        print("=============result=================", result)
                        results.append(result)
                except Exception as e:
                    print(f"❌ Error processing task: {e}")

        # Process results and create triples
        created = []
        for r in results:
            rel = r["result"].get("causal_relationship")
            if rel == "none" or not isinstance(rel, dict):
                continue

            cause = rel.get("cause")
            effect = rel.get("effect")

            e1 = r["e1"].canonical_entity or r["e1"]
            e2 = r["e2"].canonical_entity or r["e2"]

            if cause == effect or e1.id == e2.id:
                continue

            if cause == r["e1"].name and effect == r["e2"].name:
                start, end = e1, e2
            elif cause == r["e2"].name and effect == r["e1"].name:
                start, end = e2, e1
            else:
                continue

            # Check and create triple
            if not Triple.objects.filter(
                user=user,
                sentence=r["sentence"],
                entity_cause=start,
                entity_effect=end
            ).exists():
                Triple.objects.create(
                    user=user,
                    sentence=r["sentence"],
                    entity_cause=start,
                    entity_effect=end
                )
                created.append({
                    "sentence_id": r["sentence"].id,
                    "cause": start.name,
                    "effect": end.name
                })

        return JsonResponse({
            "status": "success",
            "created_triples": created,
            "count": len(created)
        }, status=200)

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
