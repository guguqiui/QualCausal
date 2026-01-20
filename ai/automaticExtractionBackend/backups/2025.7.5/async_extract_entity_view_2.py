#
# import json
# import asyncio
# from concurrent.futures import ThreadPoolExecutor
#
# from asgiref.sync import async_to_sync
# from django.http import JsonResponse
# from django.views.decorators.csrf import csrf_exempt
# from django.views.decorators.http import require_http_methods
# from langchain_core.messages import SystemMessage, HumanMessage
# from langchain_openai import ChatOpenAI, OpenAIEmbeddings
# from automaticExtractionBackend.models import Entity, SystemUser, Sentence
# from django.db import OperationalError
# from automaticExtractionBackend import settings
#
#
# # 全局线程池
# GLOBAL_THREAD_POOL = ThreadPoolExecutor(max_workers=50)
#
# # 新版 grounded theory prompt 模板
# INDICATOR_PROMPT_TEMPLATE = """
# [Instruction]
# Extract meaningful indicators from the provided sentence, which is taken from a qualitative data interview transcript. In grounded theory, an indicator refers to a word, phrase, or sentence, or a series of words, phrases, or sentences, in the materials being analyzed. Use the research overview as context to guide your extraction. Try to preserve subjects when extracting indicators.
#
# [Research Overview]
# {research_overview}
#
# [Output Format]
# Return the extracted indicators in JSON format as a simple list:
# {{
#   "indicators": [
#     "indicator1",
#     "indicator2",
#     ...
#   ]
# }}
#
# [Sentence]
# {sentence}
# """
#
#
# async def extract_entities_with_llm(llm, sentence, research_overview):
#     """Async function to extract entities using LLM"""
#     prompt = INDICATOR_PROMPT_TEMPLATE.format(
#         research_overview=research_overview,
#         sentence=sentence
#     )
#
#     messages = [
#         SystemMessage(content="You are an expert in qualitative research and grounded theory analysis."),
#         HumanMessage(content=prompt),
#     ]
#     try:
#         response = await llm.agenerate([messages])
#         response_text = response.generations[0][0].text.strip()
#         result = eval(response_text)
#         return result.get("indicators", [])
#     except Exception as e:
#         print(f"[LLM Error]: {e}")
#         return []
#
#
# def sync_get_or_create_sentence(sentence_text, user, line_number):
#     sentence, created = Sentence.objects.get_or_create(
#         text=sentence_text,
#         user=user,
#         defaults={'line_number': line_number}
#     )
#     if created or sentence.line_number == 1:
#         sentence.line_number = line_number
#         sentence.save()
#     return sentence
#
#
# def sync_save_entity_with_embedding(ent_name, user, sentence_obj, embedder):
#     ent_name = ent_name.strip()
#     if not ent_name:
#         return None
#
#     try:
#         obj, created = Entity.objects.get_or_create(
#             name=ent_name,
#             user=user,
#             sentence=sentence_obj,
#             defaults={'canonical_entity': None}
#         )
#
#         if created or obj.canonical_entity is None:
#             obj.canonical_entity = obj
#             obj.save()
#
#         if created or not obj.embeddings:
#             try:
#                 embedding_vector = embedder.embed_query(ent_name)
#                 obj.embeddings = {settings.EMBEDDING_MODEL: embedding_vector}
#                 obj.save()
#             except Exception as e:
#                 print(f"[Embedding Failed] '{ent_name}': {e}")
#
#         return {"id": obj.id, "name": obj.name}
#     except Exception as e:
#         print(f"[Error saving entity] '{ent_name}': {e}")
#         return None
#
#
# async def process_entities(entities, user, sentence_obj, embedder):
#     tasks = [
#         asyncio.get_event_loop().run_in_executor(
#             GLOBAL_THREAD_POOL,
#             sync_save_entity_with_embedding,
#             ent, user, sentence_obj, embedder
#         )
#         for ent in entities
#     ]
#     try:
#         results = await asyncio.gather(*tasks, return_exceptions=True)
#         for r in results:
#             if isinstance(r, Exception):
#                 print("error", r)
#         return [r for r in results if not isinstance(r, Exception)]
#     except Exception as e:
#         print("error", e)
#         raise
#
#
# @csrf_exempt
# @require_http_methods(["POST"])
# def extract_entity(request):
#     async def async_extract_entity():
#         try:
#             data = json.loads(request.body)
#             sentence_text = data.get("sentence", "")
#             user_id = data.get("user_id")
#             line_number = data.get("line_number", 1)
#             research_overview = data.get("research_overview", "")  # ✅ 新增字段支持
#
#             if not (sentence_text and user_id):
#                 return {"error": "No sentence or user_id provided."}, 400
#
#             try:
#                 user = await asyncio.to_thread(SystemUser.objects.get, pk=user_id)
#             except SystemUser.DoesNotExist:
#                 return {"error": "User not found."}, 404
#
#             # llm = ChatOpenAI(model="gpt-4o", temperature=0)
#             llm = ChatOpenAI(model="gpt-4.1", temperature=0)
#             embedder = OpenAIEmbeddings(model=settings.EMBEDDING_MODEL)
#
#             entities = await extract_entities_with_llm(llm, sentence_text, research_overview)
#
#             sentence_obj = await asyncio.to_thread(
#                 sync_get_or_create_sentence,
#                 sentence_text, user, line_number
#             )
#
#             saved_entities = await process_entities(
#                 entities, user, sentence_obj, embedder
#             )
#
#             return {"entities": saved_entities}, 200
#
#         except json.JSONDecodeError:
#             return {"error": "Invalid JSON."}, 400
#         except OperationalError:
#             return {"error": "Server/database connection issue."}, 503
#         except Exception as e:
#             return {"error": str(e)}, 500
#
#     loop = asyncio.new_event_loop()
#     asyncio.set_event_loop(loop)
#     try:
#         result, status_code = loop.run_until_complete(async_extract_entity())
#         return JsonResponse(result, status=status_code)
#     finally:
#         loop.close()
#


import json
import asyncio
# import nest_asyncio
from concurrent.futures import ThreadPoolExecutor
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from automaticExtractionBackend.models import Entity, SystemUser, Sentence
from django.db import OperationalError
from automaticExtractionBackend import settings

# nest_asyncio.apply()  # 允许嵌套使用事件循环（重点）

# 全局线程池
GLOBAL_THREAD_POOL = ThreadPoolExecutor(max_workers=50)

INDICATOR_PROMPT_TEMPLATE = """
[Instruction]
Extract meaningful indicators from the provided sentence, which is taken from a qualitative data interview transcript. In grounded theory, an indicator refers to a word, phrase, or sentence, or a series of words, phrases, or sentences, in the materials being analyzed. Use the research overview as context to guide your extraction. Try to preserve subjects when extracting indicators.

[Research Overview]
{research_overview}

[Output Format]
Return the extracted indicators in JSON format as a simple list:
{{
  "indicators": [
    "indicator1",
    "indicator2",
    ...
  ]
}}

[Sentence]
{sentence}
"""

async def extract_entities_with_llm(llm, sentence, research_overview):
    prompt = INDICATOR_PROMPT_TEMPLATE.format(
        research_overview=research_overview,
        sentence=sentence
    )
    messages = [
        SystemMessage(content="You are an expert in qualitative research and grounded theory analysis."),
        HumanMessage(content=prompt),
    ]
    try:
        response = await llm.agenerate([messages])
        response_text = response.generations[0][0].text.strip()
        result = eval(response_text)
        return result.get("indicators", [])
    except Exception as e:
        print(f"[LLM Error]: {e}")
        return []

def sync_get_or_create_sentence(sentence_text, user, line_number):
    sentence, created = Sentence.objects.get_or_create(
        text=sentence_text,
        user=user,
        defaults={'line_number': line_number}
    )
    if created or sentence.line_number == 1:
        sentence.line_number = line_number
        sentence.save()
    return sentence

def sync_save_entity_with_embedding(ent_name, user, sentence_obj, embedder):
    ent_name = ent_name.strip()
    if not ent_name:
        return None

    try:
        obj, created = Entity.objects.get_or_create(
            name=ent_name,
            user=user,
            sentence=sentence_obj,
            defaults={'canonical_entity': None}
        )

        if created or obj.canonical_entity is None:
            obj.canonical_entity = obj
            obj.save()

        if created or not obj.embeddings:
            try:
                embedding_vector = embedder.embed_query(ent_name)
                obj.embeddings = {settings.EMBEDDING_MODEL: embedding_vector}
                obj.save()
            except Exception as e:
                print(f"[Embedding Failed] '{ent_name}': {e}")

        return {"id": obj.id, "name": obj.name}
    except Exception as e:
        print(f"[Error saving entity] '{ent_name}': {e}")
        return None

async def process_entities(entities, user, sentence_obj, embedder):
    loop = asyncio.get_event_loop()
    tasks = [
        loop.run_in_executor(GLOBAL_THREAD_POOL, sync_save_entity_with_embedding, ent, user, sentence_obj, embedder)
        for ent in entities
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return [r for r in results if not isinstance(r, Exception)]

async def async_extract_entity(data):
    try:
        sentence_text = data.get("sentence", "")
        user_id = data.get("user_id")
        line_number = data.get("line_number", 1)
        research_overview = data.get("research_overview", "")

        if not (sentence_text and user_id):
            return {"error": "No sentence or user_id provided."}, 400

        try:
            user = await asyncio.to_thread(SystemUser.objects.get, pk=user_id)
        except SystemUser.DoesNotExist:
            return {"error": "User not found."}, 404

        llm = ChatOpenAI(model="gpt-4.1", temperature=0)
        embedder = OpenAIEmbeddings(model=settings.EMBEDDING_MODEL)

        entities = await extract_entities_with_llm(llm, sentence_text, research_overview)

        sentence_obj = await asyncio.to_thread(
            sync_get_or_create_sentence,
            sentence_text, user, line_number
        )

        saved_entities = await process_entities(entities, user, sentence_obj, embedder)

        return {"entities": saved_entities}, 200

    except json.JSONDecodeError:
        return {"error": "Invalid JSON."}, 400
    except OperationalError:
        return {"error": "Server/database connection issue."}, 503
    except Exception as e:
        return {"error": str(e)}, 500


# 同步视图 用 gunicorn 启动
# @csrf_exempt
# @require_http_methods(["POST"])
# def extract_entity(request):
#     try:
#         data = json.loads(request.body)
#     except json.JSONDecodeError:
#         return JsonResponse({"error": "Invalid JSON."}, status=400)
#
#     loop = asyncio.get_event_loop()
#     result, status_code = loop.run_until_complete(async_extract_entity(data))
#     return JsonResponse(result, status=status_code)




# @csrf_exempt
# @require_POST
# @require_http_methods(["POST"])
async def extract_entity(request):
    try:
        body = request.body
        data = json.loads(body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON."}, status=400)

    result, status_code = await async_extract_entity(data)
    return JsonResponse(result, status=status_code)
