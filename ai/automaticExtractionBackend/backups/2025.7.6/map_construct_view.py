# import asyncio
# import json
# import string
# from itertools import combinations
# from concurrent.futures import ThreadPoolExecutor
# from django.http import JsonResponse
# from django.views.decorators.csrf import csrf_exempt
# from django.views.decorators.http import require_http_methods
# from langchain_core.output_parsers import JsonOutputParser
# from langchain_openai import ChatOpenAI
# from langchain_core.messages import SystemMessage, HumanMessage
# from automaticExtractionBackend.models import SystemUser, Sentence, Triple, Construct, Entity
# import logging
# # 全局配置
#
# logger = logging.getLogger(__name__)
# parser = JsonOutputParser()
#
# # 全局线程池（根据服务器CPU核心数调整）
# # GLOBAL_THREAD_POOL = ThreadPoolExecutor(max_workers=50)  # 建议CPU核心数×2
# GLOBAL_THREAD_POOL = ThreadPoolExecutor(max_workers=200)  # 建议CPU核心数×2
#
# # 全局LLM实例（懒加载）
# _llm_instance = None
#
# @csrf_exempt
# @require_http_methods(["POST"])
# def map_all_constructs_for_user(request):
#     """
#     POST /constructs/extract_all/
#     {
#       "user_id": 1,
#       "force": true
#     }
#     """
#     try:
#         data = json.loads(request.body)
#         user_id = data.get("user_id")
#         force = data.get("force", False)
#
#         try:
#             user = SystemUser.objects.get(pk=user_id)
#         except SystemUser.DoesNotExist:
#             return JsonResponse({"error": "User not found."}, status=404)
#
#         constructs_queryset = Construct.objects.filter(user=user)
#         if not constructs_queryset.exists():
#             return JsonResponse({"error": "Please upload the constructs first."}, status=400)
#
#         constructs = [
#             {
#                 "id": c.pk,
#                 "name": c.name,
#                 "definition": c.definition,
#                 "examples": c.examples if isinstance(c.examples, list) else [],
#                 "color": c.color
#             }
#             for c in constructs_queryset
#         ]
#
#         entities = Entity.objects.filter(user=user).select_related("sentence")
#         if not entities.exists():
#             return JsonResponse({"error": "No entities found for the user."}, status=400)
#
#         llm = ChatOpenAI(model="gpt-4o", temperature=0)
#
#         # --- Step 1: 构造任务 ---
#         def make_task(entity):
#             sentence_text = entity.sentence.text if entity.sentence else ""
#             return (llm, entity, sentence_text, constructs, force)
#
#         tasks = [make_task(entity) for entity in entities if force or not entity.construct]
#
#         # --- Step 2: 包装器 ---
#         def sync_wrapper(args):
#             loop = asyncio.new_event_loop()
#             asyncio.set_event_loop(loop)
#             try:
#                 return loop.run_until_complete(process_entity_construct(*args))
#             except Exception as e:
#                 logger.error(f"Thread processing failed: {e}")
#                 return None
#             finally:
#                 loop.close()
#
#         # def sync_wrapper(args):
#         #     return asyncio.run(process_entity_construct(*args))
#
#         # --- Step 3: 执行任务 ---
#         updated = []
#         futures = [GLOBAL_THREAD_POOL.submit(sync_wrapper, task) for task in tasks]
#         for future in futures:
#             try:
#                 result = future.result(timeout=300)
#                 if result:
#                     updated.append(result)
#             except Exception as e:
#                 logger.error(f"Construct mapping task failed: {e}")
#
#         return JsonResponse({"classified_entities": updated}, status=200)
#
#     except json.JSONDecodeError:
#         return JsonResponse({"error": "Invalid JSON."}, status=400)
#     except Exception as e:
#         logger.exception("Unexpected error in map_all_constructs_for_user")
#         return JsonResponse({"error": str(e)}, status=500)
#
#
# # async def process_entity_construct(llm, entity, sentence_text, constructs, force):
# #     try:
# #         result = await classify_construct_async(entity.name, sentence_text, constructs, llm)
# #         if result:
# #             construct_obj = Construct.objects.get(pk=result['id'])
# #             entity.construct = construct_obj
# #             entity.save()
# #
# #             return {
# #                 "entity_id": entity.id,
# #                 "entity": entity.name,
# #                 "construct": result['name']
# #             }
# #     except Exception as e:
# #         logger.error(f"Error processing entity {entity.id}: {e}")
# #     return None
#
#
# from asgiref.sync import sync_to_async
#
# # async def process_entity_construct(llm, entity, sentence_text, constructs, force):
# #     try:
# #         result = await classify_construct_async(entity.name, sentence_text, constructs, llm)
# #         if result:
# #             construct_obj = await sync_to_async(Construct.objects.get)(pk=result['id'])
# #             entity.construct = construct_obj
# #             await sync_to_async(entity.save)()
# #
# #             return {
# #                 "entity_id": entity.id,
# #                 "entity": entity.name,
# #                 "construct": result['name']
# #             }
# #     except Exception as e:
# #         logger.error(f"Error processing entity {entity.id}: {e}")
# #     return None
#
#
#
# async def process_entity_construct(llm, entity, sentence_text, constructs, force):
#     max_retries = 5
#     delay = 1  # 初始重试延时（秒）
#
#     for attempt in range(1, max_retries + 1):
#         try:
#             result = await classify_construct_async(entity.name, sentence_text, constructs, llm)
#             if result:
#                 construct_obj = await sync_to_async(Construct.objects.get)(pk=result['id'])
#                 entity.construct = construct_obj
#                 await sync_to_async(entity.save)()
#
#                 return {
#                     "entity_id": entity.id,
#                     "entity": entity.name,
#                     "construct": result['name']
#                 }
#             else:
#                 logger.warning(f"Attempt {attempt}: No construct assigned to entity {entity.id}. Retrying...")
#         except Exception as e:
#             logger.error(f"Attempt {attempt}: Error processing entity {entity.id}: {e}")
#
#         await asyncio.sleep(delay)
#         delay *= 2  # 指数退避
#
#     logger.error(f"Failed to assign construct to entity {entity.id} after {max_retries} attempts.")
#     return None
#
#
#
# async def classify_construct_async(entity: str, sentence: str, constructs: list[dict], llm):
#     letters = list(string.ascii_lowercase[:len(constructs)])
#     numbered_constructs = list(zip(letters, constructs))
#
#     construct_block = "\n\n".join([
#         f"{label}. {c['name']}: {c['definition']}\nExamples: {', '.join(c.get('examples', []))}"
#         for label, c in numbered_constructs
#     ])
#
#     prompt = f"""
# Your role is to assign the most appropriate psychological construct to a given text entity. You will be provided with:
# 1. A text segment [Entity] extracted from a sentence
# 2. The complete [Sentence] from which the entity was extracted
# 3. A list of [Constructs] with their definitions and examples
#
# Answer the following question based on the [Constructs] given to you:
# Which psychological construct best describes [Entity] within the context of [Sentence]? (Select exactly one option)
#
# [Entity]
# {entity}
#
# [Sentence]
# {sentence}
#
# [Constructs]
# {construct_block}
#
# [Output Format]
# Please output your choice as a **single letter**, e.g., letters in ["a", "b", "c", ...]:
# """
#
#     messages = [
#         SystemMessage(content="You are a helpful assistant who strictly follows instructions."),
#         HumanMessage(content=prompt),
#     ]
#
#     # try:
#     #     response = await llm.ainvoke(messages)
#     #     label = response.content.strip().lower().split("label:")[-1].strip()
#     #     for l, c in numbered_constructs:
#     #         if l == label:
#     #             return c
#     # except Exception as e:
#     #     logger.error(f"LLM construct classification failed for entity '{entity}': {e}")
#     # return None
#
#     try:
#         response = await llm.ainvoke(messages)
#         content = response.content.strip().lower()
#         label = content.split("label:")[-1].strip() if "label:" in content else content
#         for l, c in numbered_constructs:
#             if l == label:
#                 return c
#         logger.warning(f"Label '{label}' not matched in constructs.")
#     except Exception as e:
#         logger.error(f"LLM construct classification failed for entity '{entity}': {e}")
#







import asyncio
import json
import string
import logging
from django.http import JsonResponse
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from automaticExtractionBackend.models import SystemUser, Sentence, Triple, Construct, Entity
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)

async def map_all_constructs_for_user(request):
    try:
        data = json.loads(request.body)
        user_id = data.get("user_id")
        force = data.get("force", False)

        # ✅ 使用 sync_to_async 获取用户
        user = await sync_to_async(SystemUser.objects.get)(pk=user_id)

        # ✅ 用 list 包装 queryset，然后用 sync_to_async
        constructs_queryset = await sync_to_async(list)(Construct.objects.filter(user=user))
        if not constructs_queryset:
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

        # ✅ 获取实体列表（select_related 要提前执行）
        entities = await sync_to_async(list)(
            Entity.objects.filter(user=user).select_related("sentence")
        )
        if not entities:
            return JsonResponse({"error": "No entities found for the user."}, status=400)

        llm = ChatOpenAI(model="gpt-4.1", temperature=0)
        # llm = ChatOpenAI(model="gpt-4o", temperature=0)

        filtered_entities = entities if force else [e for e in entities if e.construct_id is None]

        # tasks = [
        #     process_entity_construct(
        #         llm,
        #         entity,
        #         entity.sentence.text if entity.sentence else "",
        #         constructs,
        #         force
        #     )
        #     for entity in filtered_entities
        # ]

        tasks = [
            asyncio.wait_for(
                process_entity_construct(
                    llm,
                    entity,
                    entity.sentence.text if entity.sentence else "",
                    constructs,
                    force
                ),
                timeout=5  # 给每个任务设置最大超时时间（比如10秒）
            )
            for entity in filtered_entities
        ]

        # results = await asyncio.gather(*tasks)
        results = []
        for coro in asyncio.as_completed(tasks):
            try:
                result = await coro
                if result:
                    results.append(result)
            except Exception as e:
                logger.error(f"Async task failed: {e}")


        print("results:", results)
        updated = [r for r in results if r]

        return JsonResponse({"classified_entities": updated}, status=200)

    except SystemUser.DoesNotExist:
        return JsonResponse({"error": "User not found."}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON."}, status=400)
    except Exception as e:
        logger.exception("Unexpected error in map_all_constructs_for_user")
        return JsonResponse({"error": str(e)}, status=500)



#
# async def process_entity_construct(llm, entity, sentence_text, constructs, force):
#     # max_retries = 5
#     max_retries = 1
#     delay = 1
#
#     for attempt in range(1, max_retries + 1):
#         try:
#             result = await classify_construct_async(entity.name, sentence_text, constructs, llm)
#             if result:
#                 construct_obj = await sync_to_async(Construct.objects.get)(pk=result['id'])
#                 entity.construct = construct_obj
#                 await sync_to_async(entity.save)()
#
#                 return {
#                     "entity_id": entity.id,
#                     "entity": entity.name,
#                     "construct": result['name']
#                 }
#             else:
#                 logger.warning(f"Attempt {attempt}: No construct assigned to entity {entity.id}. Retrying...")
#         except Exception as e:
#             logger.error(f"Attempt {attempt}: Error processing entity {entity.id}: {e}")
#
#         await asyncio.sleep(delay)
#         delay *= 2
#
#     logger.error(f"Failed to assign construct to entity {entity.id} after {max_retries} attempts.")
#     return None



async def process_entity_construct(llm, entity, sentence_text, constructs, force):

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
    except Exception as e:
        logger.error(f"Error processing entity {entity.id}: {e}")
    return None
#
# async def classify_construct_async(entity: str, sentence: str, constructs: list[dict], llm):
#     letters = list(string.ascii_lowercase[:len(constructs)])
#     numbered_constructs = list(zip(letters, constructs))
#
#     construct_block = "\n\n".join([
#         f"{label}. {c['name']}: {c['definition']}\nExamples: {', '.join(c.get('examples', []))}"
#         for label, c in numbered_constructs
#     ])
#
#     prompt = f"""
# [Instruction]
# Your task is to assign the most appropriate concept to a given indicator (in grounded theory, an indicator refers to a word, phrase, or sentence, or a series of words, phrases, or sentences, in the materials being analyzed).
#
# You will be provided with:
# An indicator [Indicator] extracted from a paragraph
# The complete [Paragraph] from which the [Indicator] was extracted
# A list of [Concepts] with their definitions and references
#
# If you find that none of the concepts in the [Concepts] section seem appropriate, select the one that is the best fit.
#
# Answer the following question based on the [Indicator], [Paragraph], and [Concepts] given to you:
# Which concept best describes [Indicator] within the context of [Paragraph]? (Select exactly one option)
# a. construct1
# b. construct2
# c. construct3
# d. ...
#
# [Indicator]
# {entity}
#
# [Paragraph]
# {sentence}
#
# [Concepts]
# {construct_block}
#
#
# [Output Format]
# Please output your choice as a **single letter**, e.g., letters in ["a", "b", "c", ...]:
# """
#
#     # messages = [
#     #     SystemMessage(content="You are a helpful assistant who strictly follows instructions."),
#     #     HumanMessage(content=prompt),
#     # ]
#
#     try:
#         # response = await llm.ainvoke([messages])
#         response = await llm.ainvoke([
#             {"role": "system", "content": "You are a helpful assistant who strictly follows instructions."},
#             {"role": "user", "content": prompt}
#         ])
#
#         # print("response:", response)
#         content = response.content.strip().lower()
#         # print("content:", content)
#         label = content.split("label:")[-1].strip() if "label:" in content else content
#         print("label:", label)
#         for l, c in numbered_constructs:
#             if l == label:
#                 return c
#         logger.warning(f"Label '{label}' not matched in constructs.")
#     except Exception as e:
#         logger.error(f"LLM construct classification failed for entity '{entity}': {e}")
#     return None



async def classify_construct_async(entity: str, sentence: str, constructs: list[dict], llm):
    import asyncio
    letters = list(string.ascii_lowercase[:len(constructs)])
    numbered_constructs = list(zip(letters, constructs))

    construct_block = "\n\n".join([
        f"{label}. {c['name']}: {c['definition']}\nExamples: {', '.join(c.get('examples', []))}"
        for label, c in numbered_constructs
    ])

    prompt = f"""
[Instruction]
Your task is to assign the most appropriate concept to a given indicator (in grounded theory, an indicator refers to a word, phrase, or sentence, or a series of words, phrases, or sentences, in the materials being analyzed).

You will be provided with:
An indicator [Indicator] extracted from a paragraph
The complete [Paragraph] from which the [Indicator] was extracted
A list of [Concepts] with their definitions and references

If you find that none of the concepts in the [Concepts] section seem appropriate, select the one that is the best fit.

Answer the following question based on the [Indicator], [Paragraph], and [Concepts] given to you:
Which concept best describes [Indicator] within the context of [Paragraph]? (Select exactly one option)

[Indicator]
{entity}

[Paragraph]
{sentence}

[Concepts]
{construct_block}

[Output Format]
Please output your choice as a **single letter**, e.g., ["a", "b", "c", ...]
"""

    try:
        response = await asyncio.wait_for(
            llm.ainvoke([
                {"role": "system", "content": "You are a helpful assistant who strictly follows instructions."},
                {"role": "user", "content": prompt}
            ]),
            timeout=5
        )
        content = response.content.strip().lower()
        label = content.split("label:")[-1].strip() if "label:" in content else content
        print("label:", label)
        for l, c in numbered_constructs:
            if l == label:
                return c
        logger.warning(f"Label '{label}' not matched in constructs.")
    except asyncio.TimeoutError:
        logger.warning(f"Timeout when processing entity '{entity}'")
    except Exception as e:
        logger.error(f"LLM construct classification failed for entity '{entity}': {e}")
    return None


#
#
# async def classify_construct_async(entity: str, sentence: str, constructs: list[dict], llm):
#     from langchain_core.output_parsers import JsonOutputParser
#     from langchain_core.prompts import ChatPromptTemplate
#     import asyncio
#
#     letters = list(string.ascii_lowercase[:len(constructs)])
#     numbered_constructs = list(zip(letters, constructs))
#
#     construct_block = "\n\n".join([
#         f"{label}. {c['name']}: {c['definition']}\nExamples: {', '.join(c.get('examples', []))}"
#         for label, c in numbered_constructs
#     ])
#
#     parser = JsonOutputParser()  # Will expect a valid JSON like: {"label": "a"}
#
#     prompt = ChatPromptTemplate.from_messages([
#         ("system", "You are a helpful assistant that classifies concepts for grounded theory."),
#         ("user", f"""You will be given:
# - An [Indicator]: a phrase extracted from a paragraph
# - A [Paragraph]: the full sentence the indicator came from
# - A list of [Concepts] with definitions and examples
#
# Your task is to select the **most appropriate concept** from the list that fits the indicator in the context of the paragraph.
#
# Respond ONLY in this JSON format:
# {{
#   "label": "<one lowercase letter among: {labels}>"
# }}
#
# [Indicator]
# {indicator}
#
# [Paragraph]
# {paragraph}
#
# [Concepts]
# {concept_block}
# """)
#     ])
#
#     try:
#         messages = prompt.format_messages(
#             indicator=entity,
#             paragraph=sentence,
#             concept_block=construct_block,
#             labels=", ".join(letters)
#         )
#         response = await asyncio.wait_for(llm.ainvoke(messages), timeout=5)
#         parsed = parser.parse(response.content)
#
#         label = parsed["label"].strip().lower()
#         print("parsed label:", label)
#
#         for l, c in numbered_constructs:
#             if l == label:
#                 return c
#         logger.warning(f"Label '{label}' not matched in constructs.")
#     except asyncio.TimeoutError:
#         logger.warning(f"Timeout when processing entity '{entity}'")
#     except Exception as e:
#         logger.error(f"LLM construct classification failed for entity '{entity}': {e}")
#     return None
