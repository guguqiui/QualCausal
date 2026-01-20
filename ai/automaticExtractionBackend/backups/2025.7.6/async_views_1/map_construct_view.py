import asyncio
import json
import string
from itertools import combinations
from concurrent.futures import ThreadPoolExecutor

from asgiref.sync import sync_to_async
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from langchain_core.output_parsers import JsonOutputParser
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from automaticExtractionBackend.models import SystemUser, Sentence, Triple, Construct, Entity
import logging
# 全局配置

logger = logging.getLogger(__name__)
parser = JsonOutputParser()

# 全局线程池（根据服务器CPU核心数调整）
GLOBAL_THREAD_POOL = ThreadPoolExecutor(max_workers=500)  # 建议CPU核心数×2

# 全局LLM实例（懒加载）
_llm_instance = None

@csrf_exempt
@require_http_methods(["POST"])
def map_all_constructs_for_user(request):
    """
    POST /constructs/extract_all/
    {
      "user_id": 1,
      "force": true
    }
    """
    try:
        data = json.loads(request.body)
        user_id = data.get("user_id")
        force = data.get("force", False)

        try:
            user = SystemUser.objects.get(pk=user_id)
        except SystemUser.DoesNotExist:
            return JsonResponse({"error": "User not found."}, status=404)

        constructs_queryset = Construct.objects.filter(user=user)
        if not constructs_queryset.exists():
            return JsonResponse({"error": "Please upload the constructs first."}, status=400)

        constructs = [
            {
                "id": c.pk,
                "name": c.name,
                "definition": c.definition,
                "examples": c.examples if isinstance(c.examples, list) else [],
                "color": c.color
            }
            for c in constructs_queryset
        ]

        entities = Entity.objects.filter(user=user).select_related("sentence")
        if not entities.exists():
            return JsonResponse({"error": "No entities found for the user."}, status=400)

        llm = ChatOpenAI(model="gpt-4o", temperature=0)

        # --- Step 1: 构造任务 ---
        def make_task(entity):
            sentence_text = entity.sentence.text if entity.sentence else ""
            return (llm, entity, sentence_text, constructs, force)

        tasks = [make_task(entity) for entity in entities if force or not entity.construct]

        # --- Step 2: 包装器 ---
        def sync_wrapper(args):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(process_entity_construct(*args))
            except Exception as e:
                logger.error(f"Thread processing failed: {e}")
                return None
            finally:
                loop.close()

        # --- Step 3: 执行任务 ---
        updated = []
        futures = [GLOBAL_THREAD_POOL.submit(sync_wrapper, task) for task in tasks]
        for future in futures:
            try:
                result = future.result(timeout=300)
                if result:
                    updated.append(result)
            except Exception as e:
                logger.error(f"Construct mapping task failed: {e}")

        return JsonResponse({"classified_entities": updated}, status=200)

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON."}, status=400)
    except Exception as e:
        logger.exception("Unexpected error in map_all_constructs_for_user")
        return JsonResponse({"error": str(e)}, status=500)



async def process_entity_construct(llm, entity, sentence_text, constructs, force):
    max_retries = 5
    delay = 1  # 初始重试延时（秒）

    for attempt in range(1, max_retries + 1):
        try:
            result = await classify_construct_async(entity.name, sentence_text, constructs, llm)
            if result:
                construct_obj = await sync_to_async(Construct.objects.get)(pk=result['id'])
                entity.construct = construct_obj
                await sync_to_async(entity.save)()

                return {
                    "entity_id": entity.id,
                    "entity": entity.name,
                    "construct": result['name']
                }
            else:
                logger.warning(f"Attempt {attempt}: No construct assigned to entity {entity.id}. Retrying...")
        except Exception as e:
            logger.error(f"Attempt {attempt}: Error processing entity {entity.id}: {e}")

        await asyncio.sleep(delay)
        delay *= 2  # 指数退避

    logger.error(f"Failed to assign construct to entity {entity.id} after {max_retries} attempts.")
    return None



async def classify_construct_async(entity: str, sentence: str, constructs: list[dict], llm):
    letters = list(string.ascii_lowercase[:len(constructs)])
    numbered_constructs = list(zip(letters, constructs))

    construct_block = "\n\n".join([
        f"{label}. {c['name']}: {c['definition']}\nExamples: {', '.join(c.get('examples', []))}"
        for label, c in numbered_constructs
    ])

    prompt = f"""
Your role is to assign the most appropriate psychological construct to a given text entity. You will be provided with:
1. A text segment [Entity] extracted from a sentence
2. The complete [Sentence] from which the entity was extracted
3. A list of [Constructs] with their definitions and examples

Answer the following question based on the [Constructs] given to you:
Which psychological construct best describes [Entity] within the context of [Sentence]? (Select exactly one option)

[Entity]
{entity}

[Sentence]
{sentence}

[Constructs]
{construct_block}

[Output Format]
Please output your choice as a **single letter**, e.g., letters in ["a", "b", "c", ...]:
"""

    messages = [
        SystemMessage(content="You are a helpful assistant who strictly follows instructions."),
        HumanMessage(content=prompt),
    ]


    try:
        response = await llm.ainvoke(messages)
        content = response.content.strip().lower()
        label = content.split("label:")[-1].strip() if "label:" in content else content
        for l, c in numbered_constructs:
            if l == label:
                return c
        logger.warning(f"Label '{label}' not matched in constructs.")
    except Exception as e:
        logger.error(f"LLM construct classification failed for entity '{entity}': {e}")



