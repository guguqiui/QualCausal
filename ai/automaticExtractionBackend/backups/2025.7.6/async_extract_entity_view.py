#
# import json
# import asyncio
# from concurrent.futures import ThreadPoolExecutor
# from django.http import JsonResponse
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
# async def extract_entities_with_llm(llm, sentence, research_overview):
#     prompt = INDICATOR_PROMPT_TEMPLATE.format(
#         research_overview=research_overview,
#         sentence=sentence
#     )
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
# async def process_entities(entities, user, sentence_obj, embedder):
#     loop = asyncio.get_event_loop()
#     tasks = [
#         loop.run_in_executor(GLOBAL_THREAD_POOL, sync_save_entity_with_embedding, ent, user, sentence_obj, embedder)
#         for ent in entities
#     ]
#     results = await asyncio.gather(*tasks, return_exceptions=True)
#     return [r for r in results if not isinstance(r, Exception)]
#
# async def async_extract_entity(data):
#     try:
#         sentence_text = data.get("sentence", "")
#         user_id = data.get("user_id")
#         line_number = data.get("line_number", 1)
#         research_overview = data.get("research_overview", "")
#
#         if not (sentence_text and user_id):
#             return {"error": "No sentence or user_id provided."}, 400
#
#         try:
#             user = await asyncio.to_thread(SystemUser.objects.get, pk=user_id)
#         except SystemUser.DoesNotExist:
#             return {"error": "User not found."}, 404
#
#         llm = ChatOpenAI(model="gpt-4.1", temperature=0)
#         embedder = OpenAIEmbeddings(model=settings.EMBEDDING_MODEL)
#
#         entities = await extract_entities_with_llm(llm, sentence_text, research_overview)
#
#         sentence_obj = await asyncio.to_thread(
#             sync_get_or_create_sentence,
#             sentence_text, user, line_number
#         )
#
#         saved_entities = await process_entities(entities, user, sentence_obj, embedder)
#
#         return {"entities": saved_entities}, 200
#
#     except json.JSONDecodeError:
#         return {"error": "Invalid JSON."}, 400
#     except OperationalError:
#         return {"error": "Server/database connection issue."}, 503
#     except Exception as e:
#         return {"error": str(e)}, 500
#
#
# async def extract_entity(request):
#     try:
#         body = request.body
#         data = json.loads(body)
#     except json.JSONDecodeError:
#         return JsonResponse({"error": "Invalid JSON."}, status=400)
#
#     result, status_code = await async_extract_entity(data)
#     return JsonResponse(result, status=status_code)


#
# import json
# import asyncio
# import re
#
# from django.http import JsonResponse
# from django.views.decorators.csrf import csrf_exempt
# from django.views.decorators.http import require_http_methods
# from asgiref.sync import sync_to_async
# from langchain.output_parsers import ResponseSchema, StructuredOutputParser
# from langchain_core.messages import SystemMessage, HumanMessage
# from langchain_openai import ChatOpenAI, OpenAIEmbeddings
# from automaticExtractionBackend.models import Entity, SystemUser, Sentence
# from django.db import OperationalError
# from automaticExtractionBackend import settings
#
#
# @sync_to_async()
# def get_user(user_id):
#     return SystemUser.objects.get(pk=user_id)
#
#
# @sync_to_async
# def get_or_create_sentence(sentence_text, user, line_number):
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
# @sync_to_async
# def save_entity_with_embedding(ent_name, user, sentence_obj, embedder):
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
#             embedding_vector = embedder.embed_query(ent_name)
#             obj.embeddings = {settings.EMBEDDING_MODEL: embedding_vector}
#             obj.save()
#
#         return {"id": obj.id, "name": obj.name}
#     except Exception as e:
#         print(f"[Error saving entity] '{ent_name}': {e}")
#         return None
#
# #
# # async def extract_entities_with_llm(llm, sentence, research_overview):
# #     INDICATOR_PROMPT_TEMPLATE = f"""
# #     [Instruction]
# #     Extract meaningful indicators from the provided sentence, which is taken from a qualitative data interview transcript. In grounded theory, an indicator refers to a word, phrase, or sentence, or a series of words, phrases, or sentences, in the materials being analyzed. Use the research overview as context to guide your extraction. Try to preserve subjects when extracting indicators.
# #
# #     [Research Overview]
# #     {research_overview}
# #
# #     [Output Format]
# #     Return the extracted indicators in JSON format as a simple list:
# #     {{
# #       "indicators": [
# #         "indicator1",
# #         "indicator2",
# #         ...
# #       ]
# #     }}
# #
# #     [Sentence]
# #     {sentence}
# #     """
# #
# #     prompt = INDICATOR_PROMPT_TEMPLATE.format(
# #         research_overview=research_overview,
# #         sentence=sentence
# #     )
# #     messages = [
# #         SystemMessage(content="You are an expert in qualitative research and grounded theory analysis."),
# #         HumanMessage(content=prompt),
# #     ]
# #     try:
# #         response = await llm.agenerate([messages])
# #         print("response:", response)
# #         response_text = response.generations[0][0].text.strip()
# #         result = eval(response_text)
# #         print("result:", result)
# #         return result.get("indicators", [])
# #     except Exception as e:
# #         print(f"[LLM Error]: {e}")
# #         return []
#
#
# async def extract_entities_with_llm(llm, sentence, research_overview):
#     indicator_schema = ResponseSchema(
#         name="indicators",
#         description="A list of indicators extracted from the sentence, using the field name 'indicators'"
#     )
#     parser = StructuredOutputParser.from_response_schemas([indicator_schema])
#     format_instructions = parser.get_format_instructions()
#
#     prompt = f"""
# [Instruction]
# Extract meaningful indicators from the provided sentence, which is taken from a qualitative data interview transcript.
# In grounded theory, an indicator refers to a word, phrase, or sentence, or a series of words, phrases, or sentences,
# in the materials being analyzed. Use the research overview as context to guide your extraction. Try to preserve subjects when extracting indicators.
#
# [Research Overview]
# {research_overview}
#
# [Sentence]
# {sentence}
#
# {format_instructions}
# """
#
#     messages = [
#         SystemMessage(content="You are an expert in qualitative research and grounded theory analysis."),
#         HumanMessage(content=prompt),
#     ]
#
#     # try:
#     #     response = await llm.agenerate([messages])
#     #
#     #     raw_output = response.generations[0][0].text.strip()
#     #     print("raw_output:", raw_output)
#     #     parsed = parser.parse(raw_output)
#     #     return parsed.get("indicators", [])
#     # except Exception as e:
#     #     print(f"[LLM JSON Parse Error]: {e}")
#     #     return []
#
#     try:
#         response = await llm.agenerate([messages])
#         raw_output = response.generations[0][0].text.strip()
#
#         # 清理 markdown code block 包裹
#         raw_output = re.sub(r"^```json\s*|\s*```$", "", raw_output.strip())
#
#         print("cleaned_output:", raw_output)
#         parsed = parser.parse(raw_output)
#         print("parsed:", parsed)
#         return parsed.get("indicators", [])
#     except Exception as e:
#         print(f"[LLM JSON Parse Error]: {e}")
#         return []
#
#
# async def async_extract_entity(data):
#     try:
#         sentence_text = data.get("sentence", "")
#         user_id = data.get("user_id")
#         line_number = data.get("line_number", 1)
#         research_overview = data.get("research_overview", "")
#
#         if not (sentence_text and user_id):
#             return {"error": "No sentence or user_id provided."}, 400
#
#         try:
#             user = await get_user(user_id)
#         except SystemUser.DoesNotExist:
#             return {"error": "User not found."}, 404
#
#         # llm = ChatOpenAI(model="gpt-4.1", temperature=0)
#         llm = ChatOpenAI(model="gpt-4o", temperature=0)
#         embedder = OpenAIEmbeddings(model=settings.EMBEDDING_MODEL)
#
#         indicators = await extract_entities_with_llm(llm, sentence_text, research_overview)
#         sentence_obj = await get_or_create_sentence(sentence_text, user, line_number)
#
#         # print("sentence_obj:", sentence_obj)
#         tasks = [
#             save_entity_with_embedding(ent, user, sentence_obj, embedder)
#             for ent in indicators
#         ]
#         results = await asyncio.gather(*tasks, return_exceptions=True)
#         saved_entities = [r for r in results if not isinstance(r, Exception) and r]
#
#         return {"entities": saved_entities}, 200
#
#     except json.JSONDecodeError:
#         return {"error": "Invalid JSON."}, 400
#     except OperationalError:
#         return {"error": "Server/database connection issue."}, 503
#     except Exception as e:
#         return {"error": str(e)}, 500
#
#
# async def extract_entity(request):
#     try:
#         data = json.loads(request.body)
#     except json.JSONDecodeError:
#         return JsonResponse({"error": "Invalid JSON."}, status=400)
#     result, status_code = await async_extract_entity(data)
#     return JsonResponse(result, status=status_code)









#
#
# import json
# import asyncio
# import re
# from datetime import timedelta
#
# from django.http import JsonResponse
# from django.views.decorators.csrf import csrf_exempt
# from django.db import transaction
# from langchain.output_parsers import ResponseSchema, StructuredOutputParser
# from langchain_core.messages import SystemMessage, HumanMessage
# from langchain_openai import ChatOpenAI, OpenAIEmbeddings
# from automaticExtractionBackend.models import Entity, SystemUser, Sentence
# from automaticExtractionBackend import settings
# from asgiref.sync import sync_to_async
# from django.core.exceptions import ObjectDoesNotExist
#
# # 全局并发控制
# LLM_SEMAPHORE = asyncio.Semaphore(100)  # 限制并发LLM调用数量
# EMBEDDING_SEMAPHORE = asyncio.Semaphore(100)  # 限制并发嵌入生成数量
# DB_SEMAPHORE = asyncio.Semaphore(100)  # 限制并发数据库操作
#
# # 超时设置
# DB_TIMEOUT = 10.0  # 数据库操作超时
# LLM_TIMEOUT = 10.0  # LLM调用超时
# EMBEDDING_TIMEOUT = 10.0  # 嵌入生成超时
#
#
#
# @sync_to_async
# def get_user(user_id):
#     """获取用户（同步ORM包装为异步）"""
#     try:
#         return SystemUser.objects.get(pk=user_id)
#     except SystemUser.DoesNotExist:
#         raise ValueError("User not found")
#     except Exception as e:
#         raise RuntimeError(f"Database error: {str(e)}")
#
# @sync_to_async
# def get_or_create_sentence(sentence_text, user, line_number):
#     """获取或创建句子（同步ORM包装为异步）"""
#     try:
#         sentence, created = Sentence.objects.get_or_create(
#             text=sentence_text,
#             user=user,
#             defaults={'line_number': line_number}
#         )
#         if created or sentence.line_number == 1:
#             sentence.line_number = line_number
#             sentence.save()
#         return sentence
#     except Exception as e:
#         raise RuntimeError(f"Sentence creation error: {str(e)}")
#
#
# # @sync_to_async(thread_sensitive=False)
# def _save_entity(ent_name, user, sentence_obj):
#     """同步保存实体核心方法"""
#     ent_name = ent_name.strip()
#     if not ent_name:
#         return None
#
#     try:
#         with transaction.atomic():
#             obj, created = Entity.objects.get_or_create(
#                 name=ent_name,
#                 user=user,
#                 sentence=sentence_obj,
#                 defaults={'canonical_entity': None}
#             )
#
#             if created or obj.canonical_entity is None:
#                 obj.canonical_entity = obj
#                 obj.save()
#
#             return {
#                 "id": obj.id,
#                 "name": obj.name,
#                 "needs_embedding": created or not obj.embeddings
#             }
#     except Exception as e:
#         print(f"[Error saving entity] '{ent_name}': {e}")
#         return None
#
#
# @sync_to_async
# def _update_entity_embedding(entity_id, embedding):
#     """同步更新实体嵌入"""
#     try:
#         entity = Entity.objects.get(pk=entity_id)
#         entity.embeddings = {settings.EMBEDDING_MODEL: embedding}
#         entity.save()
#         return True
#     except Exception as e:
#         print(f"[Error updating embedding] entity {entity_id}: {e}")
#         return False
#
#
# async def save_entity_with_embedding(ent_name, user, sentence_obj, embedder):
#     """带嵌入生成的实体保存（异步入口）"""
#     async with DB_SEMAPHORE:
#         try:
#             # 先保存实体基本信息
#             entity_data = await asyncio.wait_for(
#                 _save_entity(ent_name, user, sentence_obj),
#                 timeout=DB_TIMEOUT
#             )
#             if not entity_data:
#                 return None
#
#             # 如果需要嵌入则生成并更新
#             if entity_data["needs_embedding"]:
#                 embedding = await generate_embedding(embedder, ent_name)
#                 success = await asyncio.wait_for(
#                     _update_entity_embedding(entity_data["id"], embedding),
#                     timeout=DB_TIMEOUT
#                 )
#                 if not success:
#                     return None
#
#             return {"id": entity_data["id"], "name": entity_data["name"]}
#         except asyncio.TimeoutError:
#             print(f"Timeout processing entity: {ent_name}")
#             return None
#         except Exception as e:
#             print(f"Error processing entity {ent_name}: {str(e)}")
#             return None
#
#
# async def generate_embedding(embedder, text):
#     """异步生成嵌入向量"""
#     async with EMBEDDING_SEMAPHORE:
#         try:
#             # 注意：embedder.embed_query是同步方法，需要用sync_to_async包装
#             return await asyncio.wait_for(
#                 sync_to_async(embedder.embed_query)(text),
#                 timeout=EMBEDDING_TIMEOUT
#             )
#         except asyncio.TimeoutError:
#             raise RuntimeError("Embedding generation timed out")
#         except Exception as e:
#             raise RuntimeError(f"Embedding error: {str(e)}")
#
#
# async def extract_entities_with_llm(llm, sentence, research_overview):
#     """使用LLM提取实体"""
#     indicator_schema = ResponseSchema(
#         name="indicators",
#         description="A list of indicators extracted from the sentence"
#     )
#     parser = StructuredOutputParser.from_response_schemas([indicator_schema])
#     format_instructions = parser.get_format_instructions()
#
#     prompt = f"""
# [Instruction]
# Extract meaningful indicators from the provided sentence, which is taken from a qualitative data interview transcript.
# In grounded theory, an indicator refers to a word, phrase, or sentence, or a series of words, phrases, or sentences,
# in the materials being analyzed. Use the research overview as context to guide your extraction. Try to preserve subjects when extracting indicators.
#
# [Research Overview]
# {research_overview}
#
# [Sentence]
# {sentence}
#
# {format_instructions}
# """
#
#     messages = [
#         SystemMessage(content="You are an expert in qualitative research and grounded theory analysis."),
#         HumanMessage(content=prompt),
#     ]
#
#     async with LLM_SEMAPHORE:
#         try:
#             response = await asyncio.wait_for(
#                 llm.agenerate([messages]),
#                 timeout=LLM_TIMEOUT
#             )
#
#             raw_output = response.generations[0][0].text.strip()
#             raw_output = re.sub(r"^```json\s*|\s*```$", "", raw_output.strip())
#
#             parsed = parser.parse(raw_output)
#             return parsed.get("indicators", [])
#         except asyncio.TimeoutError:
#             raise RuntimeError("LLM request timed out")
#         except Exception as e:
#             raise RuntimeError(f"LLM processing error: {str(e)}")
#
#
# async def async_extract_entity(data):
#     """异步处理实体提取请求"""
#     try:
#         sentence_text = data.get("sentence", "").strip()
#         user_id = data.get("user_id")
#         line_number = data.get("line_number", 1)
#         research_overview = data.get("research_overview", "").strip()
#
#         if not sentence_text:
#             return {"error": "No sentence provided."}, 400
#         if not user_id:
#             return {"error": "No user_id provided."}, 400
#
#         try:
#             user = await asyncio.wait_for(get_user(user_id), timeout=DB_TIMEOUT)
#         except asyncio.TimeoutError:
#             return {"error": "Database operation timed out"}, 504
#         except ValueError as e:
#             return {"error": str(e)}, 404
#         except RuntimeError as e:
#             return {"error": str(e)}, 500
#
#         # 初始化模型
#         llm = ChatOpenAI(model="gpt-4o", temperature=0)
#         embedder = OpenAIEmbeddings(model=settings.EMBEDDING_MODEL)
#
#         try:
#             # 提取实体
#             indicators = await extract_entities_with_llm(llm, sentence_text, research_overview)
#             sentence_obj = await asyncio.wait_for(
#                 get_or_create_sentence(sentence_text, user, line_number),
#                 timeout=DB_TIMEOUT
#             )
#
#             # 并行处理实体保存
#             tasks = [
#                 save_entity_with_embedding(ent, user, sentence_obj, embedder)
#                 for ent in indicators
#             ]
#
#             results = await asyncio.gather(*tasks, return_exceptions=True)
#
#             # 过滤结果
#             saved_entities = []
#             for i, r in enumerate(results):
#                 if isinstance(r, Exception):
#                     print(f"Error processing entity '{indicators[i]}': {str(r)}")
#                 elif r:
#                     saved_entities.append(r)
#
#             return {"entities": saved_entities}, 200
#
#         except asyncio.TimeoutError:
#             return {"error": "Processing timed out"}, 504
#         except RuntimeError as e:
#             return {"error": str(e)}, 500
#
#     except json.JSONDecodeError:
#         return {"error": "Invalid JSON."}, 400
#     except Exception as e:
#         return {"error": f"Unexpected error: {str(e)}"}, 500
#
#
# async def extract_entity(request):
#     """HTTP请求处理入口"""
#     if request.method != "POST":
#         return JsonResponse({"error": "Method not allowed"}, status=405)
#
#     try:
#         data = json.loads(request.body)
#         result, status_code = await async_extract_entity(data)
#         return JsonResponse(result, status=status_code)
#     except json.JSONDecodeError:
#         return JsonResponse({"error": "Invalid JSON"}, status=400)
#     except Exception as e:
#         return JsonResponse({"error": f"Server error: {str(e)}"}, status=500)














#
# import json
# import re
# import asyncio
# from django.db import transaction
# from asgiref.sync import sync_to_async
# from langchain.output_parsers import ResponseSchema, StructuredOutputParser
# from langchain_core.messages import SystemMessage, HumanMessage
# from langchain_openai import ChatOpenAI, OpenAIEmbeddings
# from automaticExtractionBackend.models import Entity, SystemUser, Sentence
# from automaticExtractionBackend import settings
#
# # 全局并发限制
# LLM_SEMAPHORE = asyncio.Semaphore(100)
# EMBEDDING_SEMAPHORE = asyncio.Semaphore(100)
# DB_SEMAPHORE = asyncio.Semaphore(100)
#
# DB_TIMEOUT = 15.0
# LLM_TIMEOUT = 10.0
# EMBEDDING_TIMEOUT = 10.0
#
#
# @sync_to_async
# def get_user(user_id):
#     try:
#         return SystemUser.objects.get(pk=user_id)
#     except SystemUser.DoesNotExist:
#         raise ValueError("User not found")
#     except Exception as e:
#         raise RuntimeError(f"Database error: {str(e)}")
#
#
# @sync_to_async
# def get_or_create_sentence(text, user, line_number):
#     try:
#         sentence, created = Sentence.objects.get_or_create(
#             text=text,
#             user=user,
#             defaults={'line_number': line_number}
#         )
#         if created or sentence.line_number == 1:
#             sentence.line_number = line_number
#             sentence.save()
#         return sentence
#     except Exception as e:
#         raise RuntimeError(f"Sentence creation error: {str(e)}")
#
#
# @sync_to_async
# def _save_entity(ent_name, user, sentence_obj):
#     ent_name = ent_name.strip()
#     if not ent_name:
#         return None
#
#     try:
#         with transaction.atomic():
#             obj, created = Entity.objects.get_or_create(
#                 name=ent_name,
#                 user=user,
#                 sentence=sentence_obj,
#                 defaults={'canonical_entity': None}
#             )
#             if created or obj.canonical_entity is None:
#                 obj.canonical_entity = obj
#                 obj.save()
#
#             return {
#                 "id": obj.id,
#                 "name": obj.name,
#                 "needs_embedding": created or not obj.embeddings
#             }
#     except Exception as e:
#         print(f"[Error saving entity] '{ent_name}': {e}")
#         return None
#
#
# @sync_to_async
# def _update_entity_embedding(entity_id, embedding):
#     try:
#         entity = Entity.objects.get(pk=entity_id)
#         entity.embeddings = {settings.EMBEDDING_MODEL: embedding}
#         entity.save()
#         return True
#     except Exception as e:
#         print(f"[Embedding update error] entity {entity_id}: {e}")
#         return False
#
#
# async def generate_embedding(embedder, text):
#     async with EMBEDDING_SEMAPHORE:
#         try:
#             return await asyncio.wait_for(
#                 sync_to_async(embedder.embed_query)(text),
#                 timeout=EMBEDDING_TIMEOUT
#             )
#         except asyncio.TimeoutError:
#             raise RuntimeError("Embedding generation timed out")
#         except Exception as e:
#             raise RuntimeError(f"Embedding error: {str(e)}")
#
#
# async def save_entity_with_embedding(ent_name, user, sentence_obj, embedder):
#     async with DB_SEMAPHORE:
#         try:
#             entity_data = await asyncio.wait_for(
#                 _save_entity(ent_name, user, sentence_obj),
#                 timeout=DB_TIMEOUT
#             )
#             if not entity_data:
#                 return None
#
#             if entity_data["needs_embedding"]:
#                 embedding = await generate_embedding(embedder, ent_name)
#                 success = await asyncio.wait_for(
#                     _update_entity_embedding(entity_data["id"], embedding),
#                     timeout=DB_TIMEOUT
#                 )
#                 if not success:
#                     return None
#
#             return {"id": entity_data["id"], "name": entity_data["name"]}
#         except Exception as e:
#             print(f"Entity save error: {ent_name} | {str(e)}")
#             return None
#
#
# async def extract_entities_with_llm(llm, sentence, research_overview):
#     indicator_schema = ResponseSchema(
#         name="indicators",
#         description="A list of indicators extracted from the sentence"
#     )
#     parser = StructuredOutputParser.from_response_schemas([indicator_schema])
#     format_instructions = parser.get_format_instructions()
#
#     prompt = f"""
# [Instruction]
# Extract meaningful indicators from the provided sentence, which is taken from a qualitative data interview transcript.
# In grounded theory, an indicator refers to a word, phrase, or sentence, or a series of words, phrases, or sentences,
# in the materials being analyzed. Use the research overview as context to guide your extraction. Try to preserve subjects when extracting indicators.
#
# [Research Overview]
# {research_overview}
#
# [Sentence]
# {sentence}
#
# {format_instructions}
# """
#
#     messages = [
#         SystemMessage(content="You are an expert in qualitative research and grounded theory analysis."),
#         HumanMessage(content=prompt),
#     ]
#
#     async with LLM_SEMAPHORE:
#         try:
#             response = await asyncio.wait_for(
#                 llm.agenerate([messages]),
#                 timeout=LLM_TIMEOUT
#             )
#             raw_output = response.generations[0][0].text.strip()
#             raw_output = re.sub(r"^```json\s*|\s*```$", "", raw_output)
#             parsed = parser.parse(raw_output)
#             return parsed.get("indicators", [])
#         except asyncio.TimeoutError:
#             raise RuntimeError("LLM request timed out")
#         except Exception as e:
#             raise RuntimeError(f"LLM extraction error: {str(e)}")
#
#
# async def async_extract_entity(data):
#     try:
#         sentence = data.get("sentence", "").strip()
#         user_id = data.get("user_id")
#         line_number = data.get("line_number", 1)
#         research_overview = data.get("research_overview", "").strip()
#
#         if not sentence:
#             return {"error": "No sentence provided."}, 400
#         if not user_id:
#             return {"error": "No user_id provided."}, 400
#
#         try:
#             user = await asyncio.wait_for(get_user(user_id), timeout=DB_TIMEOUT)
#         except asyncio.TimeoutError:
#             return {"error": "User lookup timed out."}, 504
#         except ValueError as e:
#             return {"error": str(e)}, 404
#         except RuntimeError as e:
#             return {"error": str(e)}, 500
#
#         llm = ChatOpenAI(model="gpt-4o", temperature=0)
#         embedder = OpenAIEmbeddings(model=settings.EMBEDDING_MODEL)
#
#         try:
#             indicators = await extract_entities_with_llm(llm, sentence, research_overview)
#             sentence_obj = await asyncio.wait_for(
#                 get_or_create_sentence(sentence, user, line_number),
#                 timeout=DB_TIMEOUT
#             )
#
#             tasks = [
#                 save_entity_with_embedding(ent, user, sentence_obj, embedder)
#                 for ent in indicators
#             ]
#             results = await asyncio.gather(*tasks, return_exceptions=True)
#
#             saved_entities = []
#             for i, r in enumerate(results):
#                 if isinstance(r, Exception):
#                     print(f"Error in entity {indicators[i]}: {str(r)}")
#                 elif r:
#                     saved_entities.append(r)
#
#             return {"entities": saved_entities}, 200
#         except Exception as e:
#             return {"error": str(e)}, 500
#
#     except json.JSONDecodeError:
#         return {"error": "Invalid JSON."}, 400
#     except Exception as e:
#         return {"error": f"Unexpected error: {str(e)}"}, 500
#
#
#
# import json
# from django.http import JsonResponse
# from django.views.decorators.csrf import csrf_exempt
# from django.views.decorators.http import require_http_methods
#
#
# async def extract_entity(request):
#     """HTTP 异步实体提取入口"""
#     try:
#         data = json.loads(request.body)
#         result, status_code = await async_extract_entity(data)
#         return JsonResponse(result, status=status_code, content_type="application/json")
#     except json.JSONDecodeError:
#         return JsonResponse({"error": "Invalid JSON"}, status=400, content_type="application/json")
#     except Exception as e:
#         return JsonResponse({"error": f"Server error: {str(e)}"}, status=500, content_type="application/json")
#















#
#
# import json
# import re
# import asyncio
# from django.db import transaction
# from django.http import JsonResponse
# from django.views.decorators.csrf import csrf_exempt
# from django.views.decorators.http import require_http_methods
# from asgiref.sync import sync_to_async
# from langchain.output_parsers import ResponseSchema, StructuredOutputParser
# from langchain_core.messages import SystemMessage, HumanMessage
# from langchain_openai import ChatOpenAI, OpenAIEmbeddings
# from automaticExtractionBackend.models import Entity, SystemUser, Sentence
# from automaticExtractionBackend import settings
#
# # 全局并发控制（保留 LLM 和 embedding）
# LLM_SEMAPHORE = asyncio.Semaphore(100)
# EMBEDDING_SEMAPHORE = asyncio.Semaphore(100)
#
# DB_TIMEOUT = 15.0
# LLM_TIMEOUT = 10.0
# EMBEDDING_TIMEOUT = 10.0
#
# # ========== 安全封装 ORM 操作（sync_to_async with thread_sensitive=True） ==========
#
# @sync_to_async(thread_sensitive=True)
# def get_user(user_id):
#     try:
#         return SystemUser.objects.get(pk=user_id)
#     except SystemUser.DoesNotExist:
#         raise ValueError("User not found")
#     except Exception as e:
#         raise RuntimeError(f"Database error: {str(e)}")
#
# @sync_to_async(thread_sensitive=True)
# def get_or_create_sentence_and_update(text, user, line_number):
#     sentence, created = Sentence.objects.get_or_create(
#         text=text,
#         user=user,
#         defaults={'line_number': line_number}
#     )
#     if created or sentence.line_number == 1:
#         sentence.line_number = line_number
#         sentence.save()
#     return sentence
#
# @sync_to_async(thread_sensitive=True)
# def save_entity(ent_name, user, sentence_obj):
#     ent_name = ent_name.strip()
#     if not ent_name:
#         return None
#
#     try:
#         with transaction.atomic():
#             obj, created = Entity.objects.get_or_create(
#                 name=ent_name,
#                 user=user,
#                 sentence=sentence_obj,
#                 defaults={'canonical_entity': None}
#             )
#             if created or obj.canonical_entity is None:
#                 obj.canonical_entity = obj
#                 obj.save()
#
#             return {
#                 "id": obj.id,
#                 "name": obj.name,
#                 "needs_embedding": created or not obj.embeddings
#             }
#     except Exception as e:
#         print(f"[Error saving entity] '{ent_name}': {e}")
#         return None
#
# @sync_to_async(thread_sensitive=True)
# def update_entity_embedding(entity_id, embedding):
#     try:
#         entity = Entity.objects.get(pk=entity_id)
#         entity.embeddings = {settings.EMBEDDING_MODEL: embedding}
#         entity.save()
#         return True
#     except Exception as e:
#         print(f"[Embedding update error] entity {entity_id}: {e}")
#         return False
#
# # ========== 异步封装模型/嵌入调用逻辑 ==========
#
# async def generate_embedding(embedder, text):
#     async with EMBEDDING_SEMAPHORE:
#         try:
#             return await asyncio.wait_for(
#                 sync_to_async(embedder.embed_query)(text),
#                 timeout=EMBEDDING_TIMEOUT
#             )
#         except asyncio.TimeoutError:
#             raise RuntimeError("Embedding generation timed out")
#         except Exception as e:
#             raise RuntimeError(f"Embedding error: {str(e)}")
#
# async def save_entity_with_embedding(ent_name, user, sentence_obj, embedder):
#     try:
#         entity_data = await asyncio.wait_for(
#             save_entity(ent_name, user, sentence_obj),
#             timeout=DB_TIMEOUT
#         )
#         if not entity_data:
#             return None
#
#         if entity_data["needs_embedding"]:
#             embedding = await generate_embedding(embedder, ent_name)
#             success = await asyncio.wait_for(
#                 update_entity_embedding(entity_data["id"], embedding),
#                 timeout=DB_TIMEOUT
#             )
#             if not success:
#                 return None
#
#         return {"id": entity_data["id"], "name": entity_data["name"]}
#     except Exception as e:
#         print(f"Entity save error: {ent_name} | {str(e)}")
#         return None
#
# # ========== LLM 调用与 JSON 格式抽取 ==========
#
# async def extract_entities_with_llm(llm, sentence, research_overview):
#     indicator_schema = ResponseSchema(
#         name="indicators",
#         description="A list of indicators extracted from the sentence"
#     )
#     parser = StructuredOutputParser.from_response_schemas([indicator_schema])
#     format_instructions = parser.get_format_instructions()
#
#     prompt = f"""
# [Instruction]
# Extract meaningful indicators from the provided sentence, which is taken from a qualitative data interview transcript.
# In grounded theory, an indicator refers to a word, phrase, or sentence, or a series of words, phrases, or sentences,
# in the materials being analyzed. Use the research overview as context to guide your extraction. Try to preserve subjects when extracting indicators.
#
# [Research Overview]
# {research_overview}
#
# [Sentence]
# {sentence}
#
# {format_instructions}
# """
#
#     messages = [
#         SystemMessage(content="You are an expert in qualitative research and grounded theory analysis."),
#         HumanMessage(content=prompt),
#     ]
#
#     async with LLM_SEMAPHORE:
#         try:
#             response = await asyncio.wait_for(
#                 llm.agenerate([messages]),
#                 timeout=LLM_TIMEOUT
#             )
#             raw_output = response.generations[0][0].text.strip()
#             raw_output = re.sub(r"^```json\s*|\s*```$", "", raw_output)
#             parsed = parser.parse(raw_output)
#             return parsed.get("indicators", [])
#         except asyncio.TimeoutError:
#             raise RuntimeError("LLM request timed out")
#         except Exception as e:
#             raise RuntimeError(f"LLM extraction error: {str(e)}")
#
# # ========== 核心异步提取逻辑 ==========
#
# async def async_extract_entity(data):
#     try:
#         sentence = data.get("sentence", "").strip()
#         user_id = data.get("user_id")
#         line_number = data.get("line_number", 1)
#         research_overview = data.get("research_overview", "").strip()
#
#         if not sentence:
#             return {"error": "No sentence provided."}, 400
#         if not user_id:
#             return {"error": "No user_id provided."}, 400
#
#         try:
#             user = await asyncio.wait_for(get_user(user_id), timeout=DB_TIMEOUT)
#         except asyncio.TimeoutError:
#             return {"error": "User lookup timed out."}, 504
#         except ValueError as e:
#             return {"error": str(e)}, 404
#         except RuntimeError as e:
#             return {"error": str(e)}, 500
#
#         llm = ChatOpenAI(model="gpt-4o", temperature=0)
#         embedder = OpenAIEmbeddings(model=settings.EMBEDDING_MODEL)
#
#         try:
#             indicators = await extract_entities_with_llm(llm, sentence, research_overview)
#
#             sentence_obj = await asyncio.wait_for(
#                 get_or_create_sentence_and_update(sentence, user, line_number),
#                 timeout=DB_TIMEOUT
#             )
#
#             tasks = [
#                 save_entity_with_embedding(ent, user, sentence_obj, embedder)
#                 for ent in indicators
#             ]
#             results = await asyncio.gather(*tasks, return_exceptions=True)
#
#             saved_entities = []
#             for i, r in enumerate(results):
#                 if isinstance(r, Exception):
#                     print(f"Error in entity {indicators[i]}: {str(r)}")
#                 elif r:
#                     saved_entities.append(r)
#
#             return {"entities": saved_entities}, 200
#         except Exception as e:
#             return {"error": str(e)}, 500
#
#     except json.JSONDecodeError:
#         return {"error": "Invalid JSON."}, 400
#     except Exception as e:
#         return {"error": f"Unexpected error: {str(e)}"}, 500
#
# # ========== 异步视图入口 ==========
#
# async def extract_entity(request):
#     """HTTP 异步实体提取入口"""
#     try:
#         data = json.loads(request.body)
#         result, status_code = await async_extract_entity(data)
#         return JsonResponse(result, status=status_code, content_type="application/json")
#     except json.JSONDecodeError:
#         return JsonResponse({"error": "Invalid JSON"}, status=400, content_type="application/json")
#     except Exception as e:
#         return JsonResponse({"error": f"Server error: {str(e)}"}, status=500, content_type="application/json")
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#


#
#
#
#
#
#


import json
import asyncio
from concurrent.futures import ThreadPoolExecutor

from asgiref.sync import async_to_sync
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from langchain.output_parsers import ResponseSchema, StructuredOutputParser
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from automaticExtractionBackend.models import Entity, SystemUser, Sentence
from django.db import OperationalError
from automaticExtractionBackend import settings


# 全局线程池
GLOBAL_THREAD_POOL = ThreadPoolExecutor(max_workers=50)


async def extract_entities_with_llm(llm, sentence, research_overview):
    response_schemas = [
        ResponseSchema(name="indicators", description="A a list of extracted grounded theory indicators")
    ]
    parser = StructuredOutputParser.from_response_schemas(response_schemas)
    format_instructions = parser.get_format_instructions()

    # 新版 grounded theory prompt 模板
    # INDICATOR_PROMPT_TEMPLATE = f"""
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

    INDICATOR_PROMPT_TEMPLATE = f"""
        [Instruction]
        Extract meaningful indicators from the provided sentence, which is taken from a qualitative data interview transcript. In grounded theory, an indicator refers to a word, phrase, or sentence, or a series of words, phrases, or sentences, in the materials being analyzed. Use the research overview as context to guide your extraction. Try to preserve subjects when extracting indicators.

        [Research Overview]
        {research_overview}


        [Sentence]
        {sentence}
        
        [Output Format]
        {format_instructions}
        """

    """Async function to extract entities using LLM"""
    prompt = INDICATOR_PROMPT_TEMPLATE.format(
        research_overview=research_overview,
        sentence=sentence
    )

    print("promt:", prompt)

    messages = [
        SystemMessage(content="You are an expert in qualitative research and grounded theory analysis."),
        HumanMessage(content=prompt),
    ]

    print("messages:", messages)
    # try:
    #     response = await llm.agenerate([messages])
    #     print(response)
    #     response_text = response.generations[0][0].text.strip()
    #     result = eval(response_text)
    #     print("result:", result)
    #     return result.get("indicators", [])
    # except Exception as e:
    #     print(f"[LLM Error]: {e}")
    #     return []

    try:
        response = await llm.agenerate([messages])
        print("response:", response)

        response_text = response.generations[0][0].text.strip()
        print("result:", response_text)

        try:
            result = parser.parse(response_text)
            return result.get("indicators", [])
        except Exception as parse_err:
            print(f"[Parsing Error]: {parse_err}")
            return []
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
    tasks = [
        asyncio.get_event_loop().run_in_executor(
            GLOBAL_THREAD_POOL,
            sync_save_entity_with_embedding,
            ent, user, sentence_obj, embedder
        )
        for ent in entities
    ]
    try:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in results:
            if isinstance(r, Exception):
                print("error", r)
        return [r for r in results if not isinstance(r, Exception)]
    except Exception as e:
        print("error", e)
        raise


@csrf_exempt
@require_http_methods(["POST"])
def extract_entity(request):
    async def async_extract_entity():
        try:
            data = json.loads(request.body)
            sentence_text = data.get("sentence", "")
            user_id = data.get("user_id")
            line_number = data.get("line_number", 1)
            research_overview = data.get("research_overview", "")  # ✅ 新增字段支持

            if not (sentence_text and user_id):
                return {"error": "No sentence or user_id provided."}, 400

            try:
                user = await asyncio.to_thread(SystemUser.objects.get, pk=user_id)
            except SystemUser.DoesNotExist:
                return {"error": "User not found."}, 404

            llm = ChatOpenAI(model="gpt-4o", temperature=0)
            # llm = ChatOpenAI(model="gpt-4.1", temperature=0)
            embedder = OpenAIEmbeddings(model=settings.EMBEDDING_MODEL)

            entities = await extract_entities_with_llm(llm, sentence_text, research_overview)

            sentence_obj = await asyncio.to_thread(
                sync_get_or_create_sentence,
                sentence_text, user, line_number
            )

            saved_entities = await process_entities(
                entities, user, sentence_obj, embedder
            )

            return {"entities": saved_entities}, 200

        except json.JSONDecodeError:
            return {"error": "Invalid JSON."}, 400
        except OperationalError:
            return {"error": "Server/database connection issue."}, 503
        except Exception as e:
            return {"error": str(e)}, 500

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result, status_code = loop.run_until_complete(async_extract_entity())
        return JsonResponse(result, status=status_code)
    finally:
        loop.close()
