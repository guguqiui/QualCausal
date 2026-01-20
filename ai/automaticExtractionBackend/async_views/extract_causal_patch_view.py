import itertools
import json
import asyncio
import logging
import re
from itertools import combinations
from concurrent.futures import ThreadPoolExecutor
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from openai import RateLimitError, APIError, APIStatusError # Import APIStatusError for more specific handling

# Global configurations
from automaticExtractionBackend.models import SystemUser, Sentence, Triple
from automaticExtractionBackend.settings import OPENAI_KEYS
import nest_asyncio

nest_asyncio.apply()

logger = logging.getLogger(__name__)
# Use a context manager or ensure proper shutdown for ThreadPoolExecutor in a real app
# GLOBAL_THREAD_POOL = ThreadPoolExecutor(max_workers=100)
GLOBAL_THREAD_POOL = ThreadPoolExecutor(max_workers=300)
BATCH_SIZE = 5

# Assuming OPENAI_KEYS is a list of API keys
api_key_cycle = itertools.cycle(OPENAI_KEYS)  # Create an infinite cycle iterator

def get_llm_instance(max_retries=3) -> ChatOpenAI:
    """
    Get a new LLM instance based on the user_id, cycling through the API keys to balance the usage.
    """
    if not OPENAI_KEYS:
        raise ValueError("No OpenAI API keys configured")

    # Get the next available API key in the cycle (this will not repeat the same key until all have been used)
    selected_key = next(api_key_cycle)

    # Log the selection of the API key for debugging purposes
    print(f"Selecting API key: {selected_key}")

    llm = ChatOpenAI(
        openai_api_key=selected_key,
        model="gpt-4o",
        temperature=0,
        max_retries=max_retries,
        timeout=120)  # Increased timeout for robustness
    return llm






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
        # If no markdown block, assume the whole text is JSON
        return text.strip()
    except Exception as e:
        logger.error(f"Error extracting JSON from markdown: {e}")
        return None


async def analyze_sentence_async(sentence, user_id):
    entities = list(sentence.entities.all())
    if len(entities) < 2:
        return []  # Return an empty list if there are not enough entities

    # Generate entity pairs
    pairs = list(combinations(entities, 2))

    prompts = []
    for e1, e2 in pairs:
        construct1 = e1.construct.name if e1.construct else "unknown"
        construct2 = e2.construct.name if e2.construct else "unknown"

        prompt_text = f"""
- Sentence: {sentence.text}
- Entity 1: {e1.name} ({construct1})
- Entity 2: {e2.name} ({construct2})
"""
        prompts.append((e1, e2, prompt_text))

    llm = get_llm_instance(user_id)

    messages_lst = [
        [SystemMessage(content=CAUSAL_PROMPT), HumanMessage(content=prompt[2])]
        for prompt in prompts
    ]

    results = []
    try:
        # Using agenerate for batched async calls to the LLM
        response = await llm.agenerate(messages_lst)

        for generation_list, (e1, e2, prompt) in zip(response.generations, prompts):
            for generation in generation_list:
                parsed_text = extract_json_from_markdown(generation.text)
                if parsed_text:
                    try:
                        result = json.loads(parsed_text)
                        final_result = {
                            "sentence": sentence,
                            "e1": e1,
                            "e2": e2,
                            "result": result
                        }
                        results.append(final_result)
                    except json.JSONDecodeError as e:
                        logger.error(f"Error parsing JSON response for sentence '{sentence.id}', entities '{e1.name}', '{e2.name}': {e}. Raw response: {parsed_text}")
                        continue
                else:
                    logger.warning(f"Could not extract JSON from LLM response for sentence '{sentence.id}', entities '{e1.name}', '{e2.name}'. Raw response: {generation.text}")
        return results
    except RateLimitError as e:
        logger.error(f"Rate limit exceeded for user {user_id}: {str(e)}")
        # You might want to re-raise or handle this differently depending on your retry policy
        raise
    except APIStatusError as e: # Catching more specific OpenAI API errors
        logger.error(f"OpenAI API status error for user {user_id} (Code: {e.status_code}, Message: {e.response}): {str(e)}")
        raise
    except APIError as e:
        logger.error(f"OpenAI API general error for user {user_id}: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in analyze_sentence_async for user {user_id}: {str(e)}", exc_info=True)
        raise # Re-raise to be caught by the thread pool's .result()


def process_sentence_sync_wrapper(sentence, user_id):
    """
    Synchronous wrapper to run the async analyze_sentence_async function.
    Each thread gets its own isolated event loop for this task.
    """
    try:
        return asyncio.run(analyze_sentence_async(sentence, user_id))
    except (RateLimitError, APIError, APIStatusError) as e:
        logger.error(f"LLM processing failed for sentence {sentence.id}: {e}")
        return None # Or a specific error indicator
    except Exception as e:
        logger.error(f"Unexpected error in process_sentence_sync_wrapper for sentence {sentence.id}: {e}", exc_info=True)
        return None


# 汇总句子的所有分析结果
def process_sentences(sentences, user_id):
    futures = []
    for sentence in sentences:
        futures.append(GLOBAL_THREAD_POOL.submit(process_sentence_sync_wrapper, sentence, user_id))

    results = []
    # Collect results, potentially with individual error handling
    for future in futures:
        try:
            # You can make the timeout more granular or dynamic
            result = future.result(timeout=300)
            if result:
                results.extend(result)
        except Exception as e:
            # This catches exceptions from future.result(), which would be
            # exceptions raised by process_sentence_sync_wrapper (and thus analyze_sentence_async)
            logger.error(f"Failed to get result for a sentence: {e}")
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
        # Use .select_related() for foreign keys to reduce queries
        user = SystemUser.objects.get(pk=user_id)
        sentences = Sentence.objects.filter(user=user).prefetch_related("entities", "entities__construct")

        if not sentences.exists():
            return JsonResponse({
                "status": "success",
                "message": "No sentences found for the user.",
                "created_triples": [],
                "count": 0,
                "analyzed_pairs": 0
            }, status=200)

        results = process_sentences(sentences, user_id)

        created = []
        for r in results:
            # Ensure 'result' and 'causal_relationship' keys exist
            if not isinstance(r, dict) or "result" not in r or not (rel := r["result"].get("causal_relationship")):
                logger.warning(f"Skipping malformed result: {r}")
                continue

            if rel == "none" or not isinstance(rel, dict):
                continue

            # 确定因果关系方向
            e1 = r["e1"]
            e2 = r["e2"]

            cause_name = rel.get("cause")
            effect_name = rel.get("effect")

            if not cause_name or not effect_name:
                logger.warning(f"Causal relationship missing 'cause' or 'effect' keys in result: {rel}")
                continue

            # Handle canonical entities if they exist
            final_e1 = e1.canonical_entity if e1.canonical_entity else e1
            final_e2 = e2.canonical_entity if e2.canonical_entity else e2

            # Determine actual cause and effect entity objects based on names
            start_entity = None
            end_entity = None

            if cause_name == e1.name and effect_name == e2.name:
                start_entity = final_e1
                end_entity = final_e2
            elif cause_name == e2.name and effect_name == e1.name:
                start_entity = final_e2
                end_entity = final_e1
            else:
                logger.warning(f"Could not match cause '{cause_name}' and effect '{effect_name}' to input entities '{e1.name}' and '{e2.name}' for sentence {r['sentence'].id}. Skipping.")
                continue

            # Prevent self-causation if LLM makes a mistake
            if start_entity == end_entity:
                logger.warning(f"Skipping self-causation for sentence {r['sentence'].id}, entity {start_entity.name}")
                continue

            # Create unique triple
            triple, created_flag = Triple.objects.get_or_create(
                user=user,
                sentence=r["sentence"],
                entity_cause=start_entity,
                entity_effect=end_entity,
                defaults={"user": user}
            )

            if created_flag:
                created.append({
                    "sentence_id": r["sentence"].id,
                    "cause": start_entity.name,
                    "effect": end_entity.name,
                    "triple_id": triple.id # Added triple ID for tracking
                })

        return JsonResponse({
            "status": "success",
            "created_triples": created,
            "count": len(created),
            "analyzed_pairs": len(results)
        }, status=200)

    except SystemUser.DoesNotExist:
        return JsonResponse({"error": f"User with ID not found."}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON in request body"}, status=400)
    except Exception as e:
        logger.exception("An unexpected error occurred in extract_causal_relations view.")
        return JsonResponse({"error": f"Internal server error: {str(e)}"}, status=500)