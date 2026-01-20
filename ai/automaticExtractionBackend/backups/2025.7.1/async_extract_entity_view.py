# import json
# import asyncio
#
# from django.http import JsonResponse
# from django.views.decorators.csrf import csrf_exempt
# from django.views.decorators.http import require_http_methods
# from langchain_core.messages import SystemMessage, HumanMessage
# from langchain_openai import ChatOpenAI, OpenAIEmbeddings
#
# from automaticExtractionBackend.models import Entity, SystemUser, Sentence, Construct
# from django.db import OperationalError
#
#
# # @csrf_exempt
# # @require_http_methods(["POST"])
# # async def extract_entity(request):
# #     try:
# #         data = json.loads(request.body)
# #         sentence = data.get("sentence", "")
# #         user_id = data.get("user_id")
# #         line_number = data.get("line_number", 1)
# #
# #         if not (sentence and user_id):
# #             return JsonResponse({"error": "No sentence or user_id provided."}, status=400)
# #
# #         try:
# #             user = await asyncio.to_thread(SystemUser.objects.get, pk=user_id)
# #         except SystemUser.DoesNotExist:
# #             return JsonResponse({"error": "User not found."}, status=404)
# #
# #         entities = await extract_entities(sentence, user, line_number)
# #         return JsonResponse({"entities": entities}, status=200)
# #
# #     except json.JSONDecodeError:
# #         return JsonResponse({"error": "Invalid JSON."}, status=400)
# #     except OperationalError as e:
# #         return JsonResponse({"error": "Server/database connection issue."}, status=503)
# #     except Exception as e:
# #         return JsonResponse({"error": str(e)}, status=500)
#
# @csrf_exempt
# @require_http_methods(["POST"])
# async def extract_entity(request):
#     try:
#         data = json.loads(request.body)
#         sentence = data.get("sentence", "")
#         user_id = data.get("user_id")
#         line_number = data.get("line_number", 1)
#
#         if not (sentence and user_id):
#             return JsonResponse({"error": "No sentence or user_id provided."}, status=400)
#
#         try:
#             user = await SystemUser.objects.aget(pk=user_id)
#         except SystemUser.DoesNotExist:
#             return JsonResponse({"error": "User not found."}, status=404)
#
#         entities = await extract_entities(sentence, user, line_number)
#         return JsonResponse({"entities": entities}, status=200)
#
#     except json.JSONDecodeError:
#         return JsonResponse({"error": "Invalid JSON."}, status=400)
#     except OperationalError as e:
#         return JsonResponse({"error": "Server/database connection issue."}, status=503)
#     except Exception as e:
#         return JsonResponse({"error": str(e)}, status=500)
#
#
#
# async def extract_entities(sentence: str, user, line_number) -> list[str]:
#     llm = ChatOpenAI(model="gpt-4o", temperature=0)
#
#     system_prompt = """
#     Extract meaningful entities from the provided sentence, which is taken from a qualitative data interview transcript.
#
#     An entity is any distinct and meaningful phrase or component from the sentence that captures a complete thought, concept,
#     action, feeling, belief, observation, or any other significant element of expression.
#
#     Return the extracted entities in JSON format as a simple list
#
#     [Example]
#     Input: "No, I would not feel angry, I would feel concerned and try to talk to them to calm them down. It is out of the ordinary behaviour for them, I do not like seeing people angry or arguments so I would try and defuse the situation."
#
#     [Output]:
#     {
#       "entities": [
#         "would not feel angry",
#         "would feel concerned",
#         "try to talk to them",
#         "calm them down",
#         "It is out of the ordinary behaviour for them",
#         "I do not like seeing people angry",
#         "I do not like arguments",
#         "try and defuse the situation"
#       ]
#     }
#     """
#
#     messages = [
#         SystemMessage(content=system_prompt),
#         HumanMessage(content=sentence),
#     ]
#
#     response = await llm.agenerate([messages])
#     try:
#         response_dict = eval(response.content)  # assuming well-formatted output
#         entities = response_dict.get("entities", [])
#     except Exception as e:
#         print(e)
#         entities = []
#
#     sentence_obj, created = await Sentence.objects.aget_or_create(
#         text=sentence,
#         user=user,
#         defaults={'line_number': line_number}
#     )
#
#     if created or sentence_obj.line_number == 1:
#         sentence_obj.line_number = line_number
#         await sentence_obj.asave()
#
#     saved_names = []
#     embedder = OpenAIEmbeddings(model="embedding-model")
#
#     async def save_entity_with_embedding(ent_name: str):
#         ent_name = ent_name.strip()
#         if not ent_name:
#             return None
#
#         obj, created = await Entity.objects.aget_or_create(
#             name=ent_name,
#             user=user,
#             sentence=sentence_obj,
#             defaults={'canonical_entity': None}
#         )
#
#         if created or obj.canonical_entity is None:
#             obj.canonical_entity = obj
#             await obj.asave()
#
#         if created or not obj.embeddings:
#             try:
#                 embedding_vector = await embedder.aembed_query(ent_name)
#                 obj.embeddings = {
#                     "embedding-model": embedding_vector
#                 }
#                 await obj.asave()
#             except Exception as e:
#                 print(f"[Embedding Failed] '{ent_name}': {e}")
#
#         return {"id": obj.id, "name": obj.name}
#
#     # async execution of saving entities
#     tasks = [save_entity_with_embedding(ent) for ent in entities]
#     results = await asyncio.gather(*tasks)
#
#     print("results:", results)
#
#     saved_names.extend([r for r in results if r is not None])
#     return saved_names
#
# #
# # async def extract_entities(sentence: str, user, line_number) -> list[str]:
# #     llm = ChatOpenAI(model="gpt-4o", temperature=0)
# #
# #     # system_prompt = """
# #     # Extract meaningful entities from the provided sentence, which is taken from a qualitative data interview transcript.
# #     #
# #     # An entity is any distinct and meaningful phrase or component from the sentence that captures a complete thought, concept,
# #     # action, feeling, belief, observation, or any other significant element of expression.
# #     #
# #     # Return the extracted entities in JSON format as a simple list
# #     # """
# #     system_prompt = """
# #     Extract meaningful entities from the provided sentence, which is taken from a qualitative data interview transcript.
# #
# #     An entity is any distinct and meaningful phrase or component from the sentence that captures a complete thought, concept,
# #     action, feeling, belief, observation, or any other significant element of expression.
# #
# #     Return the extracted entities in JSON format as a simple list
# #
# #     [Example]
# #     Input: "No, I would not feel angry, I would feel concerned and try to talk to them to calm them down. It is out of the ordinary behaviour for them, I do not like seeing people angry or arguments so I would try and defuse the situation."
# #
# #     [Output]:
# #     {
# #       "entities": [
# #         "would not feel angry",
# #         "would feel concerned",
# #         "try to talk to them",
# #         "calm them down",
# #         "It is out of the ordinary behaviour for them",
# #         "I do not like seeing people angry",
# #         "I do not like arguments",
# #         "try and defuse the situation"
# #       ]
# #     }
# #     """
# #
# #     messages = [
# #         SystemMessage(content=system_prompt),
# #         HumanMessage(content=sentence),
# #     ]
# #
# #     response = await llm.agenerate(messages)
# #     try:
# #         response_dict = eval(response.content)  # assuming well-formatted output
# #         entities = response_dict.get("entities", [])
# #     except Exception as e:
# #         print(e)
# #         entities = []
# #
# #     sentence_obj, created = await asyncio.to_thread(Sentence.objects.get_or_create, text=sentence, user=user)
# #
# #     if created or sentence_obj.line_number == 1:
# #         sentence_obj.line_number = line_number
# #         await asyncio.to_thread(sentence_obj.save)
# #
# #     saved_names = []
# #     embedder = OpenAIEmbeddings(model="embedding-model")
# #
# #     async def save_entity_with_embedding(ent_name: str):
# #         ent_name = ent_name.strip()
# #         if not ent_name:
# #             return None
# #
# #         obj, created = await asyncio.to_thread(Entity.objects.get_or_create, name=ent_name, user=user, sentence=sentence_obj)
# #
# #         if created or obj.canonical_entity is None:
# #             obj.canonical_entity = obj
# #             await asyncio.to_thread(obj.save)
# #
# #         if created or not obj.embeddings:
# #             try:
# #                 embedding_vector = embedder.embed_query(ent_name)
# #                 obj.embeddings = {
# #                     "embedding-model": embedding_vector
# #                 }
# #                 await asyncio.to_thread(obj.save)
# #             except Exception as e:
# #                 print(f"[Embedding Failed] '{ent_name}': {e}")
# #
# #         return {"id": obj.id, "name": obj.name}
# #
# #     # async execution of saving entities
# #     tasks = [save_entity_with_embedding(ent) for ent in entities]
# #     results = await asyncio.gather(*tasks)
# #
# #     saved_names.extend(results)
# #     return saved_names
#
#
# @csrf_exempt
# @require_http_methods(["POST"])
# async def update_entity_construct(request):
#     """POST /api/update_entity_construct/
#     Body: {
#       "entity_id": 123,
#       "construct_id": 456
#     }"""
#     try:
#         data = json.loads(request.body)
#         user_id = data.get("user_id")
#         entity_id = data.get("entity_id")
#         construct_id = data.get("construct_id")
#
#         if not (entity_id and construct_id):
#             return JsonResponse({"error": "entity_id and construct_id are required."}, status=400)
#
#         entity = await asyncio.to_thread(Entity.objects.get, pk=entity_id)
#         construct = await asyncio.to_thread(Construct.objects.get, pk=construct_id)
#
#         entity.construct = construct
#         await asyncio.to_thread(entity.save)
#
#         return JsonResponse({"message": f"Entity {entity_id} updated to construct {construct_id}."}, status=200)
#
#     except Entity.DoesNotExist:
#         return JsonResponse({"error": "Entity not found."}, status=404)
#     except Construct.DoesNotExist:
#         return JsonResponse({"error": "Construct not found."}, status=404)
#     except json.JSONDecodeError:
#         return JsonResponse({"error": "Invalid JSON."}, status=400)
#     except Exception as e:
#         return JsonResponse({"error": str(e)}, status=500)
#
#
# @csrf_exempt
# @require_http_methods(["POST"])
# async def update_entity_name(request):
#     """POST /api/update_entity_name/
#     Body: {
#       "entity_id": 123,
#       "new_name": "updated entity name"
#     }"""
#     try:
#         data = json.loads(request.body)
#         entity_id = data.get("entity_id")
#         new_name = data.get("new_name", "").strip()
#
#         if not (entity_id and new_name):
#             return JsonResponse({"error": "entity_id and new_name are required."}, status=400)
#
#         entity = await asyncio.to_thread(Entity.objects.get, pk=entity_id)
#         entity.name = new_name
#         await asyncio.to_thread(entity.save)
#
#         return JsonResponse({"message": f"Entity {entity_id} name updated to '{new_name}'."}, status=200)
#
#     except Entity.DoesNotExist:
#         return JsonResponse({"error": "Entity not found."}, status=404)
#     except json.JSONDecodeError:
#         return JsonResponse({"error": "Invalid JSON."}, status=400)
#     except Exception as e:
#         return JsonResponse({"error": str(e)}, status=500)
#
#
# @csrf_exempt
# @require_http_methods(["POST"])
# async def delete_entity(request):
#     """POST /delete_entity/
#     Body: {
#       "entity_id": 123,
#       "user_id": 456
#     }"""
#     try:
#         data = json.loads(request.body)
#         entity_id = data.get("entity_id")
#         user_id = data.get("user_id")
#
#         if not (entity_id and user_id):
#             return JsonResponse({"error": "entity_id and user_id are required."}, status=400)
#
#         entity = await asyncio.to_thread(Entity.objects.get, pk=entity_id)
#
#         if entity.user.pk != user_id:
#             return JsonResponse({"error": "Permission denied: entity does not belong to this user."}, status=403)
#
#         await asyncio.to_thread(entity.delete)
#         return JsonResponse({"message": f"Entity {entity_id} deleted successfully."}, status=200)
#
#     except Entity.DoesNotExist:
#         return JsonResponse({"error": "Entity not found."}, status=404)
#     except json.JSONDecodeError:
#         return JsonResponse({"error": "Invalid JSON."}, status=400)
#     except Exception as e:
#         return JsonResponse({"error": str(e)}, status=500)



import json
import asyncio

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from automaticExtractionBackend import settings
from automaticExtractionBackend.models import Entity, SystemUser, Sentence, Construct
from django.db import OperationalError

#
# @csrf_exempt
# @require_http_methods(["POST"])
# async def extract_entity(request):
#     try:
#         # 解析请求数据
#         data = json.loads(request.body)
#         sentence = data.get("sentence", "")
#         user_id = data.get("user_id")
#         line_number = data.get("line_number", 1)
#
#         # 检查必需字段
#         if not (sentence and user_id):
#             return JsonResponse({"error": "No sentence or user_id provided."}, status=400)
#
#         # 获取用户对象
#         try:
#             user = await SystemUser.objects.aget(pk=user_id)
#             print("user:", user)
#         except SystemUser.DoesNotExist:
#             return JsonResponse({"error": "User not found."}, status=404)
#
#         # 提取实体
#         entities = await extract_entities(sentence, user, line_number)
#         return JsonResponse({"entities": entities}, status=200)
#
#     except json.JSONDecodeError:
#         return JsonResponse({"error": "Invalid JSON."}, status=400)
#     except OperationalError as e:
#         return JsonResponse({"error": "Server/database connection issue."}, status=503)
#     except Exception as e:
#         return JsonResponse({"error": str(e)}, status=500)
#
#
# async def extract_entities(sentence: str, user, line_number) -> list[str]:
#     # 创建 LLM 实例
#     llm = ChatOpenAI(model="gpt-4o", temperature=0)
#
#     # 系统提示
#     system_prompt = """
#     Extract meaningful entities from the provided sentence, which is taken from a qualitative data interview transcript.
#
#     An entity is any distinct and meaningful phrase or component from the sentence that captures a complete thought, concept,
#     action, feeling, belief, observation, or any other significant element of expression.
#
#     Return the extracted entities in JSON format as a simple list
#
#     [Example]
#     Input: "No, I would not feel angry, I would feel concerned and try to talk to them to calm them down. It is out of the ordinary behaviour for them, I do not like seeing people angry or arguments so I would try and defuse the situation."
#
#     [Output]:
#     {
#       "entities": [
#         "would not feel angry",
#         "would feel concerned",
#         "try to talk to them",
#         "calm them down",
#         "It is out of the ordinary behaviour for them",
#         "I do not like seeing people angry",
#         "I do not like arguments",
#         "try and defuse the situation"
#       ]
#     }
#     """
#
#     # 生成消息
#     messages = [
#         SystemMessage(content=system_prompt),
#         HumanMessage(content=sentence),
#     ]
#
#     # 调用 LLM 生成响应并等待
#     response = await llm.agenerate([messages])
#     print("response:", response)
#     try:
#         response_dict = eval(response.content)  # assuming well-formatted output
#         entities = response_dict.get("entities", [])
#     except Exception as e:
#         print(e)
#         entities = []
#
#     # 创建或获取句子对象
#     sentence_obj, created = await Sentence.objects.aget_or_create(
#         text=sentence,
#         user=user,
#         defaults={'line_number': line_number}
#     )
#
#     # 更新句子对象行号
#     if created or sentence_obj.line_number == 1:
#         sentence_obj.line_number = line_number
#         await sentence_obj.asave()
#
#     # 保存实体
#     saved_names = []
#     embedder = OpenAIEmbeddings(model="embedding-model")
#
#     async def save_entity_with_embedding(ent_name: str):
#         ent_name = ent_name.strip()
#         if not ent_name:
#             return None
#
#         # 创建或获取实体对象
#         obj, created = await Entity.objects.aget_or_create(
#             name=ent_name,
#             user=user,
#             sentence=sentence_obj,
#             defaults={'canonical_entity': None}
#         )
#
#         # 设置规范实体
#         if created or obj.canonical_entity is None:
#             obj.canonical_entity = obj
#             await obj.asave()
#
#         # 嵌入存储
#         if created or not obj.embeddings:
#             try:
#                 embedding_vector = await embedder.aembed_query(ent_name)
#                 obj.embeddings = {
#                     "embedding-model": embedding_vector
#                 }
#                 await obj.asave()
#             except Exception as e:
#                 print(f"[Embedding Failed] '{ent_name}': {e}")
#
#         return {"id": obj.id, "name": obj.name}
#
#     # 异步执行实体保存任务
#     tasks = [save_entity_with_embedding(ent) for ent in entities]
#     results = await asyncio.gather(*tasks)
#
#     print("results:", results)
#
#     # 收集已保存的实体
#     saved_names.extend([r for r in results if r is not None])
#     return saved_names




import json
import asyncio

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from automaticExtractionBackend.models import Entity, SystemUser, Sentence, Construct
from django.db import OperationalError


@csrf_exempt
@require_http_methods(["POST"])
def extract_entity(request):
    try:
        # 解析请求数据
        data = json.loads(request.body)
        sentence = data.get("sentence", "")
        user_id = data.get("user_id")
        line_number = data.get("line_number", 1)

        # 检查必需字段
        if not (sentence and user_id):
            return JsonResponse({"error": "No sentence or user_id provided."}, status=400)

        # 获取用户对象
        try:
            user = SystemUser.objects.get(pk=user_id)
            print("user:", user)
        except SystemUser.DoesNotExist:
            return JsonResponse({"error": "User not found."}, status=404)

        # 提取实体
        # 将 extract_entities 设置为异步并使用 asyncio 来处理
        entities = asyncio.run(extract_entities(sentence, user, line_number))
        return JsonResponse({"entities": entities}, status=200)

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON."}, status=400)
    except OperationalError as e:
        return JsonResponse({"error": "Server/database connection issue."}, status=503)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

#
# async def extract_entities(sentence: str, user, line_number) -> list[str]:
#     # 创建 LLM 实例
#     llm = ChatOpenAI(model="gpt-4o", temperature=0)
#
#     # 系统提示
#     system_prompt = """
#     Extract meaningful entities from the provided sentence, which is taken from a qualitative data interview transcript.
#
#     An entity is any distinct and meaningful phrase or component from the sentence that captures a complete thought, concept,
#     action, feeling, belief, observation, or any other significant element of expression.
#
#     Return the extracted entities in JSON format as a simple list
#
#     [Example]
#     Input: "No, I would not feel angry, I would feel concerned and try to talk to them to calm them down. It is out of the ordinary behaviour for them, I do not like seeing people angry or arguments so I would try and defuse the situation."
#
#     [Output]:
#     {
#       "entities": [
#         "would not feel angry",
#         "would feel concerned",
#         "try to talk to them",
#         "calm them down",
#         "It is out of the ordinary behaviour for them",
#         "I do not like seeing people angry",
#         "I do not like arguments",
#         "try and defuse the situation"
#       ]
#     }
#     """
#
#     # 生成消息
#     messages = [
#         SystemMessage(content=system_prompt),
#         HumanMessage(content=sentence),
#     ]
#
#     # 调用 LLM 生成响应并等待
#     response = await llm.agenerate([messages])
#     print("response:", response)
#
#     try:
#         # 提取生成的文本内容
#         # response_text = response.generations[0].text.strip()  # 从 'generations' 中提取生成文本
#         response_text = response.generations[0][0].text.strip()
#         # response_text = response.generations[0].message.content.strip()
#         print("response_text", response_text)
#         response_dict = json.loads(response_text)  # 解析为 JSON
#         entities = response_dict.get("entities", [])
#         print("entities:", entities)
#     except Exception as e:
#         print(e)
#         entities = []
#
#     # 创建或获取句子对象
#     sentence_obj, created = await asyncio.to_thread(Sentence.objects.aget_or_create, text=sentence, user=user, defaults={'line_number': line_number})
#     # 将原本的 aget_or_create 替换为 get_or_create
#
#     # 更新句子对象行号
#     if created or sentence_obj.line_number == 1:
#         sentence_obj.line_number = line_number
#         await asyncio.to_thread(sentence_obj.save)
#
#     # 保存实体
#     saved_names = []
#     embedder = OpenAIEmbeddings(model=settings.EMBEDDING_MODEL)
#     # embedder = OpenAIEmbeddings(model="embedding-model")
#     print("embedder:", embedder)
#
#     async def save_entity_with_embedding(ent_name: str):
#         ent_name = ent_name.strip()
#         if not ent_name:
#             return None
#
#         # 创建或获取实体对象
#         obj, created = await asyncio.to_thread(Entity.objects.aget_or_create, name=ent_name, user=user, sentence=sentence_obj, defaults={'canonical_entity': None})
#
#         # 设置规范实体
#         if created or obj.canonical_entity is None:
#             obj.canonical_entity = obj
#             try:
#                 await asyncio.to_thread(obj.save)
#             except Exception as e:
#                 print(f"[数据库保存失败] '{ent_name}': {e}")
#                 return None
#
#             # await asyncio.to_thread(obj.save)
#
#         # 嵌入存储
#         if created or not obj.embeddings:
#             try:
#                 embedding_vector = await embedder.aembed_query(ent_name)
#                 obj.embeddings = {
#                     "embedding-model": embedding_vector
#                 }
#                 await asyncio.to_thread(obj.save)
#             except Exception as e:
#                 print(f"[Embedding Failed] '{ent_name}': {e}")
#
#         return {"id": obj.id, "name": obj.name}
#
#     # 异步执行实体保存任务
#     tasks = [save_entity_with_embedding(ent) for ent in entities]
#     results = await asyncio.gather(*tasks)
#
#     print("results:", results)
#
#     # 收集已保存的实体
#     saved_names.extend([r for r in results if r is not None])
#     return saved_names



async def extract_entities(sentence: str, user, line_number) -> list[str]:
    # 创建 LLM 实例
    llm = ChatOpenAI(model="gpt-4o", temperature=0)

    # 系统提示
    system_prompt = """
    Extract meaningful entities from the provided sentence, which is taken from a qualitative data interview transcript.

    An entity is any distinct and meaningful phrase or component from the sentence that captures a complete thought, concept,
    action, feeling, belief, observation, or any other significant element of expression.

    Return the extracted entities in JSON format as a simple list

    [Example]
    Input: "No, I would not feel angry, I would feel concerned and try to talk to them to calm them down. It is out of the ordinary behaviour for them, I do not like seeing people angry or arguments so I would try and defuse the situation."

    [Output]:
    {
      "entities": [
        "would not feel angry",
        "would feel concerned",
        "try to talk to them",
        "calm them down",
        "It is out of the ordinary behaviour for them",
        "I do not like seeing people angry",
        "I do not like arguments",
        "try and defuse the situation"
      ]
    }
    """

    # 生成消息
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=sentence),
    ]

    # 调用 LLM 生成响应并等待
    response = await llm.agenerate([messages])
    print("response:", response)

    try:
        # 提取生成的文本内容
        response_text = response.generations[0][0].text.strip()
        print("response_text:", response_text)
        response_dict = json.loads(response_text)  # 解析为 JSON
        entities = response_dict.get("entities", [])
        print("entities:", entities)
    except Exception as e:
        print(f"[Error extracting entities]: {e}")
        entities = []

    # 创建或获取句子对象
    sentence_obj, created = await asyncio.to_thread(Sentence.objects.get_or_create, text=sentence, user=user, defaults={'line_number': line_number})

    # 更新句子对象行号
    if created or sentence_obj.line_number == 1:
        sentence_obj.line_number = line_number
        await asyncio.to_thread(sentence_obj.save)

    # 保存实体
    saved_names = []
    embedder = OpenAIEmbeddings(model=settings.EMBEDDING_MODEL)

    async def save_entity_with_embedding(ent_name: str):
        ent_name = ent_name.strip()
        if not ent_name:
            return None

        try:
            # 创建或获取实体对象
            obj, created = await asyncio.to_thread(Entity.objects.get_or_create, name=ent_name, user=user, sentence=sentence_obj, defaults={'canonical_entity': None})

            # 设置规范实体
            if created or obj.canonical_entity is None:
                obj.canonical_entity = obj
                await asyncio.to_thread(obj.save)

            # 嵌入存储
            if created or not obj.embeddings:
                try:
                    embedding_vector = await embedder.aembed_query(ent_name)
                    obj.embeddings = {
                        "embedding-model": embedding_vector
                    }
                    await asyncio.to_thread(obj.save)
                except Exception as e:
                    print(f"[Embedding Failed] '{ent_name}': {e}")

            return {"id": obj.id, "name": obj.name}
        except Exception as e:
            print(f"[Error saving entity] '{ent_name}': {e}")
            return None

    # 异步执行实体保存任务
    tasks = [save_entity_with_embedding(ent) for ent in entities]
    results = await asyncio.gather(*tasks)

    print("results:", results)

    # 收集已保存的实体
    saved_names.extend([r for r in results if r is not None])
    return saved_names