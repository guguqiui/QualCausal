

import json
import asyncio
import logging
import random
import re
from itertools import combinations
from concurrent.futures import ThreadPoolExecutor
from langchain_core.output_parsers import JsonOutputParser
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from openai import RateLimitError

# Global configurations
from automaticExtractionBackend import settings
from automaticExtractionBackend.models import SystemUser, Sentence, Triple

logger = logging.getLogger(__name__)
GLOBAL_THREAD_POOL = ThreadPoolExecutor(max_workers=100)

# LLM prompt
# CAUSAL_PROMPT = """
# [Instruction]
# Analyze the given sentence and the two identified entities with their constructs. Determine if there is a meaningful causal relationship between these entities based on the text evidence.
# A causal relationship exists when one entity (cause) leads to, results in, or influences another entity (effect).
# [Input Format]
# - Sentence: The complete sentence from a qualitative data interview transcript
# - Entity 1: The first entity with its construct type in parentheses
# - Entity 2: The second entity with its construct type in parentheses
# [Output Format]
# {
#   "causal_relationship": {
#     "cause": "entity that is the cause",
#     "relationship": "lead to",
#     "effect": "entity that is the effect"
#   }
# }
#
# Make sure to return a valid JSON structure with double quotes!!!!
# """


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


# Helper function to extract JSON from markdown
def extract_json_from_markdown(text):
    try:
        match = re.search(r"```json(.*?)```", text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return text.strip()
    except Exception as e:
        logger.error(f"Error extracting JSON from markdown: {e}")
        return None


async def analyze_sentence_async(sentence):
    entities = list(sentence.entities.all())
    if len(entities) < 2:
        return []  # Return an empty list if there are not enough entities

    # Generate entity pairs
    pairs = list(combinations(entities, 2))

    prompts = []
    for e1, e2 in pairs:
        construct1 = e1.construct.name if e1.construct else "unknown"
        construct2 = e2.construct.name if e2.construct else "unknown"

        # Include e1 and e2 in the prompt explicitly
        prompt = f"""
        - Sentence: {sentence.text}
        - Entity 1: {e1.name} ({construct1})
        - Entity 2: {e2.name} ({construct2})
        """
        prompts.append((e1, e2, prompt))  # Include e1 and e2 as part of the prompt tuple

    # Send prompts to LLM for batch processing
    llm = ChatOpenAI(
        openai_api_key=random.choice(settings.OPENAI_KEYS),
        model="gpt-4o",
        temperature=0,
    )
    messages_lst = [
        [SystemMessage(content=CAUSAL_PROMPT), HumanMessage(content=prompt[2])]
        for prompt in prompts
    ]

    try:
        results = []
        response = await llm.agenerate(messages_lst)  # Batch processing

        for generation_list, (e1, e2, prompt) in zip(response.generations, prompts):
            for generation in generation_list:
                parsed_text = extract_json_from_markdown(generation.text)
                if parsed_text:
                    result = json.loads(parsed_text)
                    print("result:", result)
                    # Preserve e1 and e2 along with the result
                    final_result = {
                        "sentence": sentence,
                        "e1": e1,
                        "e2": e2,
                        "result": result
                    }
                    results.append(final_result)
        return results
    except RateLimitError as e:
        logger.error(f"Rate limit exceeded: {str(e)}")
        return {"error": "Rate limit exceeded. Try again later."}
    except Exception as e:
        logger.error(f"Error processing sentence: {str(e)}")
        return None


# Helper function to process multiple sentences concurrently
def process_sentence_async(sentence):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(analyze_sentence_async(sentence))
        return result
    finally:
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()



# # 汇总句子的所有分析结果
def process_sentences(sentences):
    futures = []
    for sentence in sentences:
        futures.append(GLOBAL_THREAD_POOL.submit(process_sentence_async, sentence))

    results = []
    for future in futures:
        try:
            result = future.result(timeout=300)
            if result:
                results.extend(result)
        except Exception as e:
            logger.error(f"Error processing sentence: {str(e)}")
    return results

# Function to process and store results
@csrf_exempt
@require_http_methods(["POST"])
def extract_causal_relations(request):
    try:
        data = json.loads(request.body)
        user_id = data.get("user_id")
        if not user_id:
            return JsonResponse({"error": "Missing user_id"}, status=400)

        # Fetch user and sentence data
        user = SystemUser.objects.get(pk=user_id)
        sentences = Sentence.objects.filter(user=user).prefetch_related("entities", "entities__construct")
        results = process_sentences(sentences)

        created = []
        for r in results:
            if not (rel := r["result"].get("causal_relationship")):
                continue
            if rel == "none" or not isinstance(rel, dict):
                continue

            # 确定因果关系方向
            e1 = r["e1"].canonical_entity or r["e1"]
            e2 = r["e2"].canonical_entity or r["e2"]

            if (cause := rel.get("cause")) == (effect := rel.get("effect")):
                continue

            if cause == r["e1"].name and effect == r["e2"].name:
                start, end = e1, e2
            elif cause == r["e2"].name and effect == r["e1"].name:
                start, end = e2, e1
            else:
                continue

            # 创建唯一三元组
            _, created_flag = Triple.objects.get_or_create(
                user=user,
                sentence=r["sentence"],
                entity_cause=start,
                entity_effect=end,
                defaults={"user": user}  # 仅创建时需要的字段
            )

            if created_flag:
                created.append({
                    "sentence_id": r["sentence"].id,
                    "cause": start.name,
                    "effect": end.name
                })

        return JsonResponse({
            "status": "success",
            "created_triples": created,
            "count": len(created),
            "analyzed_pairs": len(results)
        }, status=200)

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        logger.exception("Unexpected error in extract_causal_relations")
        return JsonResponse({"error": str(e)}, status=500)

#
#
# import json
# import asyncio
# import logging
# import random
# import re
# from itertools import combinations
# from concurrent.futures import ThreadPoolExecutor
# from langchain_core.output_parsers import JsonOutputParser
# from langchain_openai import ChatOpenAI
# from langchain_core.messages import SystemMessage, HumanMessage
# from django.http import JsonResponse
# from django.views.decorators.csrf import csrf_exempt
# from django.views.decorators.http import require_http_methods
# from openai import RateLimitError
# from asgiref.sync import sync_to_async
# from django.core.exceptions import ObjectDoesNotExist
#
# # Global configurations
# from automaticExtractionBackend import settings
# from automaticExtractionBackend.models import SystemUser, Sentence, Triple
#
# logger = logging.getLogger(__name__)
# GLOBAL_THREAD_POOL = ThreadPoolExecutor(max_workers=100)
#
# # LLM prompt (same as before)
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
#
#
# def extract_json_from_markdown(text):
#     try:
#         match = re.search(r"```json(.*?)```", text, re.DOTALL)
#         if match:
#             return match.group(1).strip()
#         return text.strip()
#     except Exception as e:
#         logger.error(f"Error extracting JSON from markdown: {e}")
#         return None
#
#
# async def analyze_entity_pair(sentence, e1, e2, api_key):
#     """Analyze a single entity pair with a dedicated LLM instance"""
#     construct1 = await sync_to_async(getattr)(e1.construct, "name") if e1.construct else "unknown"
#     construct2 = await sync_to_async(getattr)(e2.construct, "name") if e2.construct else "unknown"
#
#     prompt = f"""
#     - Sentence: {sentence.text}
#     - Entity 1: {e1.name} ({construct1})
#     - Entity 2: {e2.name} ({construct2})
#     """
#
#     llm = ChatOpenAI(
#         openai_api_key=api_key,
#         model="gpt-4o",
#         temperature=0,
#     )
#
#     try:
#         response = await llm.agenerate([[SystemMessage(content=CAUSAL_PROMPT), HumanMessage(content=prompt)]])
#         parsed_text = extract_json_from_markdown(response.generations[0][0].text)
#         if parsed_text:
#             result = json.loads(parsed_text)
#             return {
#                 "sentence": sentence,
#                 "e1": e1,
#                 "e2": e2,
#                 "result": result
#             }
#     except Exception as e:
#         logger.error(f"Error analyzing entity pair: {str(e)}")
#     return None
#
#
# async def analyze_sentence_async(sentence):
#     entities = await sync_to_async(list)(sentence.entities.all())
#     if len(entities) < 2:
#         return []
#
#     pairs = list(combinations(entities, 2))
#     results = []
#
#     # Create a new API key for this request
#     api_key = random.choice(settings.OPENAI_KEYS)
#
#     # Process all pairs concurrently for this sentence
#     tasks = [analyze_entity_pair(sentence, e1, e2, api_key) for e1, e2 in pairs]
#     sentence_results = await asyncio.gather(*tasks, return_exceptions=True)
#
#     for result in sentence_results:
#         if result and not isinstance(result, Exception):
#             results.append(result)
#
#     return results
#
#
# async def process_sentences_async(sentences):
#     """Process all sentences asynchronously"""
#     tasks = [analyze_sentence_async(sentence) for sentence in sentences]
#     all_results = await asyncio.gather(*tasks, return_exceptions=True)
#
#     results = []
#     for result in all_results:
#         if isinstance(result, Exception):
#             logger.error(f"Error processing sentence: {str(result)}")
#         elif result:
#             results.extend(result)
#
#     return results
#
#
# async def async_extract_causals(user_id):
#     """Async version of the main extraction logic"""
#     try:
#         user = await sync_to_async(SystemUser.objects.get)(pk=user_id)
#         sentences = await sync_to_async(list)(
#             Sentence.objects.filter(user=user).prefetch_related("entities", "entities__construct"))
#
#         results = await process_sentences_async(sentences)
#
#         created = []
#         for r in results:
#             if not r or not (rel := r["result"].get("causal_relationship")):
#                 continue
#             if rel == "none" or not isinstance(rel, dict):
#                 continue
#
#             e1 = r["e1"].canonical_entity or r["e1"]
#             e2 = r["e2"].canonical_entity or r["e2"]
#
#             if (cause := rel.get("cause")) == (effect := rel.get("effect")):
#                 continue
#
#             if cause == r["e1"].name and effect == r["e2"].name:
#                 start, end = e1, e2
#             elif cause == r["e2"].name and effect == r["e1"].name:
#                 start, end = e2, e1
#             else:
#                 continue
#
#             _, created_flag = await sync_to_async(Triple.objects.get_or_create)(
#                 user=user,
#                 sentence=r["sentence"],
#                 entity_cause=start,
#                 entity_effect=end,
#                 defaults={"user": user}
#             )
#
#             if created_flag:
#                 created.append({
#                     "sentence_id": r["sentence"].id,
#                     "cause": start.name,
#                     "effect": end.name
#                 })
#
#         return {
#             "status": "success",
#             "created_triples": created,
#             "count": len(created),
#             "analyzed_pairs": len(results)
#         }
#
#     except ObjectDoesNotExist:
#         return {"error": "User not found"}
#     except Exception as e:
#         logger.exception("Unexpected error in async_extract_causals")
#         return {"error": str(e)}
#
#
# @csrf_exempt
# @require_http_methods(["POST"])
# def extract_causal_relations(request):
#     try:
#         data = json.loads(request.body)
#         user_id = data.get("user_id")
#         if not user_id:
#             return JsonResponse({"error": "Missing user_id"}, status=400)
#
#         # Run the async processing in a dedicated event loop
#         loop = asyncio.new_event_loop()
#         asyncio.set_event_loop(loop)
#         try:
#             result = loop.run_until_complete(async_extract_causals(user_id))
#             if "error" in result:
#                 return JsonResponse({"error": result["error"]}, status=400)
#             return JsonResponse(result, status=200)
#         finally:
#             loop.close()
#
#     except json.JSONDecodeError:
#         return JsonResponse({"error": "Invalid JSON"}, status=400)
#     except Exception as e:
#         logger.exception("Unexpected error in extract_causal_relations")
#         return JsonResponse({"error": str(e)}, status=500)