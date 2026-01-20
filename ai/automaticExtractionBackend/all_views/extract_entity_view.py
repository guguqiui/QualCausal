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

from automaticExtractionBackend import settings
from automaticExtractionBackend.models import Entity, SystemUser, Sentence, Construct

#
# @csrf_exempt
# @require_http_methods(["POST"])
# def extract_entity(request):
#     try:
#         data = json.loads(request.body)
#         sentence = data.get("sentence", "")
#         user_id = data.get("user_id")
#         line_number = data.get("line_number", 1)  # 默认为 1
#         user = SystemUser.objects.get(pk=user_id)
#
#         if not (sentence and user_id):
#             return JsonResponse({"error": "No sentence or user_id provided."}, status=400)
#
#         entities = extract_entities(sentence, user, line_number)
#         return JsonResponse({"entities": entities}, status=200)
#
#     except json.JSONDecodeError:
#         return JsonResponse({"error": "Invalid JSON."}, status=400)


from django.db import OperationalError

@csrf_exempt
@require_http_methods(["POST"])
def extract_entity(request):
    try:
        data = json.loads(request.body)
        sentence = data.get("sentence", "")
        user_id = data.get("user_id")
        line_number = data.get("line_number", 1)

        if not (sentence and user_id):
            return JsonResponse({"error": "No sentence or user_id provided."}, status=400)

        try:
            user = SystemUser.objects.get(pk=user_id)
        except SystemUser.DoesNotExist:
            return JsonResponse({"error": "User not found."}, status=404)

        entities = extract_entities(sentence, user, line_number)
        return JsonResponse({"entities": entities}, status=200)

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON."}, status=400)
    except OperationalError as e:
        return JsonResponse({"error": "Server/database connection issue."}, status=503)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def extract_entities(sentence: str, user, line_number) -> list[str]:
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

#     system_prompt = """
# [Instruction]
# Extract meaningful indicators from the provided sentence, which is taken from a qualitative data interview transcript. In grounded theory, an indicator refers to a word, phrase, or sentence, or a series of words, phrases, or sentences, in the materials being analyzed.
#
# [Output Format]
# Return the extracted indicators in JSON format as a simple list:
# {
#   "indicators": [
#     "indicator1",
#     "indicator2",
#     "indicator3",
#     ...
#   ]
# }
#
# [Example]
# Input: "No, I would not feel angry, I would feel concerned and try to talk to them to calm them down. It is out of the ordinary behaviour for them, I do not like seeing people angry or arguments so I would try and defuse the situation."
# Output:
# {
#   "indicators": [
#     "I would not feel angry",
#     "I would feel concerned",
#     "try to talk to them to calm them down",
#     "It is out of the ordinary behaviour for them",
#     "I do not like seeing people angry or arguments",
#     "I would try and defuse the situation"
#   ]
# }
#
# [Sentence]
# (The specific sentence to be extracted)
#     """
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
    sentence_obj, created = Sentence.objects.get_or_create(text=sentence, user=user)

    # 如果是新建的，或 line_number 还没有被设置，更新它
    if created or sentence_obj.line_number == 1:
        sentence_obj.line_number = line_number
        sentence_obj.save()


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

    # with ThreadPoolExecutor(max_workers=5) as executor:
    with ThreadPoolExecutor(max_workers=20) as executor:
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




@csrf_exempt
@require_http_methods(["POST"])
def update_entity_name(request):
    """POST /api/update_entity_name/
    Body: {
      "entity_id": 123,
      "new_name": "updated entity name"
    }"""
    try:
        data = json.loads(request.body)
        entity_id = data.get("entity_id")
        new_name = data.get("new_name", "").strip()

        if not (entity_id and new_name):
            return JsonResponse({"error": "entity_id and new_name are required."}, status=400)

        entity = Entity.objects.get(pk=entity_id)
        entity.name = new_name
        entity.save()

        return JsonResponse({"message": f"Entity {entity_id} name updated to '{new_name}'."}, status=200)

    except Entity.DoesNotExist:
        return JsonResponse({"error": "Entity not found."}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON."}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)




@csrf_exempt
@require_http_methods(["POST"])
def delete_entity(request):
    """POST /delete_entity/
    Body: {
      "entity_id": 123,
      "user_id": 456
    }"""
    try:
        data = json.loads(request.body)
        entity_id = data.get("entity_id")
        user_id = data.get("user_id")

        if not (entity_id and user_id):
            return JsonResponse({"error": "entity_id and user_id are required."}, status=400)

        entity = Entity.objects.get(pk=entity_id)

        if entity.user.pk != user_id:
            return JsonResponse({"error": "Permission denied: entity does not belong to this user."}, status=403)

        entity.delete()
        return JsonResponse({"message": f"Entity {entity_id} deleted successfully."}, status=200)

    except Entity.DoesNotExist:
        return JsonResponse({"error": "Entity not found."}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON."}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
