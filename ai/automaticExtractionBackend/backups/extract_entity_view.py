"""
 @file: extract_entity_view.py
 @Time    : 2025/4/2
 @Author  : Peinuan qin
 """
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

# from automaticExtractionBackend.tools.extract_entity import extract_entities
from automaticExtractionBackend import settings
from automaticExtractionBackend.models import Entity, SystemUser, Sentence, Construct


@csrf_exempt
@require_http_methods(["POST"])
def extract_entity(request):
    try:
        data = json.loads(request.body)
        sentence = data.get("sentence", "")
        user_id = data.get("user_id")
        user = SystemUser.objects.get(pk=user_id)

        if not (sentence and user_id):
            return JsonResponse({"error": "No sentence or user_id provided."}, status=400)

        entities = extract_entities(sentence, user)
        return JsonResponse({"entities": entities}, status=200)

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON."}, status=400)

# def extract_entities(sentence: str, user) -> list[str]:
#     # from sentence_transformers import SentenceTransformer
#     # embedding_models = {
#     #     "smpnet": SentenceTransformer("all-mpnet-base-v2"),
#     #     "sminilm": SentenceTransformer("all-MiniLM-L6-v2"),
#     #     "sdistilroberta": SentenceTransformer("all-distilroberta-v1")
#     # }
#
#     llm = ChatOpenAI(model="gpt-4o", temperature=0)
#
#     system_prompt = """
# Extract meaningful entities from the provided sentence, which is taken from a qualitative data interview transcript.
#
# An entity is any distinct and meaningful phrase or component from the sentence that captures a complete thought, concept,
# action, feeling, belief, observation, or any other significant element of expression.
#
# Return the extracted entities in JSON format as a simple list
#
# [Example]
# Input: "No, I would not feel angry, I would feel concerned and try to talk to them to calm them down. It is out of the ordinary behaviour for them, I do not like seeing people angry or arguments so I would try and defuse the situation."
#
# [Output]:
# {
#   "entities": [
#     "would not feel angry",
#     "would feel concerned",
#     "try to talk to them",
#     "calm them down",
#     "It is out of the ordinary behaviour for them",
#     "I do not like seeing people angry",
#     "I do not like arguments",
#     "try and defuse the situation"
#   ]
# }
#
# """
#     messages = [
#         SystemMessage(content=system_prompt),
#         HumanMessage(content=sentence),
#     ]
#
#     response = llm(messages)
#     try:
#         response_dict = eval(response.content)  # assuming well-formatted output
#         entities = response_dict.get("entities", [])
#     except Exception:
#         entities = []
#
#     # ✅ 如果该句子不存在，就创建它
#     sentence_obj, _ = Sentence.objects.get_or_create(text=sentence, user=user)
#
#     # 保存到数据库（不重复）
#     saved_names = []
#     for ent in entities:
#         ent_name = ent.strip()
#         if not ent_name:
#             continue
#
#         # # 简单启发式：根据内容中包含的关键词决定 construct（可后续完善）
#         # if any(word in ent_name.lower() for word in ["feel", "angry", "concerned", "emotion"]):
#         #     construct = "emotion"
#         # elif any(word in ent_name.lower() for word in ["talk", "defuse", "calm", "do", "try"]):
#         #     construct = "action"
#         # else:
#         #     construct = "belief"
#
#         # 避免重复插入
#         obj, created = Entity.objects.get_or_create(name=ent_name, user=user, sentence=sentence_obj)
#
#         """
#         创建 embeddings
#         """
#         # if created or not obj.embeddings:
#         #     obj.embeddings = {
#         #         name: model.encode(ent_name).tolist()
#         #         for name, model in embedding_models.items()
#         #     }
#         #     obj.save()
#
#         if created or not obj.embeddings:
#             try:
#                 embedder = OpenAIEmbeddings(model=settings.EMBEDDING_MODEL)  # or your preferred model
#                 embedding_vector = embedder.embed_query(ent_name)
#                 obj.embeddings = {
#                     settings.EMBEDDING_MODEL: embedding_vector
#                 }
#                 obj.save()
#             except Exception as e:
#                 print(f"Embedding failed for '{ent_name}': {e}")
#
#         saved_names.append(obj.name)
#
#     return saved_names



def extract_entities(sentence: str, user) -> list[str]:
    llm = ChatOpenAI(model="gpt-4o", temperature=0)

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

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=sentence),
    ]

    response = llm(messages)
    try:
        response_dict = eval(response.content)  # assuming well-formatted output
        entities = response_dict.get("entities", [])
    except Exception:
        entities = []

    # ✅ 如果该句子不存在，就创建它
    sentence_obj, _ = Sentence.objects.get_or_create(text=sentence, user=user)

    saved_names = []
    embedder = OpenAIEmbeddings(model=settings.EMBEDDING_MODEL)

    def save_entity_with_embedding(ent_name: str):
        ent_name = ent_name.strip()
        if not ent_name:
            return None

        obj, created = Entity.objects.get_or_create(name=ent_name, user=user, sentence=sentence_obj)

        # ✅ 初始化 canonical_entity 为自身（新建或为空时）
        if created or obj.canonical_entity is None:
            obj.canonical_entity = obj
            obj.save()

        if created or not obj.embeddings:
            try:
                embedding_vector = embedder.embed_query(ent_name)
                obj.embeddings = {
                    settings.EMBEDDING_MODEL: embedding_vector
                }
                obj.save()
            except Exception as e:
                print(f"[Embedding Failed] '{ent_name}': {e}")
        # return obj.name
        return {"id": obj.id, "name": obj.name}

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(save_entity_with_embedding, ent) for ent in entities]
        for future in as_completed(futures):
            result = future.result()
            if result:
                saved_names.append(result)

    return saved_names


@csrf_exempt
@require_http_methods(["POST"])
def update_entity_construct(request):
    """POST /api/update_entity_construct/
    Body: {
      "entity_id": 123,
      "construct_id": 456
    }"""

    try:
        data = json.loads(request.body)
        user_id = data.get("user_id")
        entity_id = data.get("entity_id")
        construct_id = data.get("construct_id")

        if not (entity_id and construct_id):
            return JsonResponse({"error": "entity_id and construct_id are required."}, status=400)


        entity = Entity.objects.get(pk=entity_id)
        construct = Construct.objects.get(pk=construct_id)

        entity.construct = construct
        entity.save()

        return JsonResponse({"message": f"Entity {entity_id} updated to construct {construct_id}."}, status=200)

    except Entity.DoesNotExist:
        return JsonResponse({"error": "Entity not found."}, status=404)
    except Construct.DoesNotExist:
        return JsonResponse({"error": "Construct not found."}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON."}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


