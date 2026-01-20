"""
 @file: construct_view.py
 @Time    : 2025/4/3
 @Author  : Peinuan qin
 """
# views_construct.py


from concurrent.futures import ThreadPoolExecutor, as_completed
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
from django.http import JsonResponse
from automaticExtractionBackend.models import Construct, SystemUser, Entity

import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from automaticExtractionBackend.models import Construct, SystemUser, Entity

"""
POST /constructs/add/
{
  "user_id": 1,
  "name": "Emotion",
  "definition": "Emotional states...",
  "examples": ["feeling sad", "being scared"]
}
"""

@require_http_methods(["GET"])
def get_constructs(request):
    user_id = request.GET.get("user_id")
    constructs = Construct.objects.filter(user_id=user_id)

    data = [
        {
            "id": c.id,
            "name": c.name,
            "definition": c.definition,
            "examples": c.examples,
        }
        for c in constructs
    ]
    return JsonResponse({"constructs": data}, status=200)


@csrf_exempt
@require_http_methods(["POST"])
def add_construct(request):
    try:
        body = json.loads(request.body)
        user_id = body.get("user_id")
        name = body.get("name")
        definition = body.get("definition")
        examples = body.get("examples", [])

        user = SystemUser.objects.get(id=user_id)
        construct = Construct.objects.create(
            user=user,
            name=name,
            definition=definition,
            examples=examples,
        )
        return JsonResponse({"id": construct.id}, status=201)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)



"""
POST /constructs/upload/?user_id=1
[
  {
    "name": "signaling event",
    "definition": "represented symptomatic behaviors...",
    "examples": ["Avery feeling judged by others"]
  },
  ...
]
"""
@csrf_exempt
@require_http_methods(["POST"])
def upload_constructs_from_json(request):
    try:
        data = json.loads(request.body)
        user_id = data.get("user_id")
        user = SystemUser.objects.get(id=user_id)
        constructs = data.get("constructs")

        if not isinstance(constructs, list):
            return JsonResponse({"error": "Uploaded JSON should be a list of constructs."}, status=400)

        created = []
        for item in constructs:
            name = item.get("name")
            definition = item.get("definition")
            examples = item.get("examples", [])

            if not (name and definition):
                continue

            construct, _ = Construct.objects.get_or_create(
                user=user,
                name=name,
                definition=definition,
                examples=examples
            )
            created.append({
                "id": construct.id,
                "name": construct.name
            })

        return JsonResponse({"created": created}, status=201)

    except SystemUser.DoesNotExist:
        return JsonResponse({"error": "User not found."}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@csrf_exempt
@require_http_methods(["POST"])
def update_construct(request, id):
    try:
        body = json.loads(request.body)
        construct = Construct.objects.get(id=id)

        construct.name = body.get("name", construct.name)
        construct.definition = body.get("definition", construct.definition)
        construct.examples = body.get("examples", construct.examples)
        construct.save()

        return JsonResponse({"message": "Construct updated."})
    except Construct.DoesNotExist:
        return JsonResponse({"error": "Construct not found."}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@csrf_exempt
@require_http_methods(["POST"])
def delete_construct(request, id):
    try:
        construct = Construct.objects.get(id=id)
        construct.delete()
        return JsonResponse({"message": "Construct deleted."})
    except Construct.DoesNotExist:
        return JsonResponse({"error": "Construct not found."}, status=404)



@csrf_exempt
@require_http_methods(["POST"])
def map_construct(request):
    """
    输入 entity、sentence 和 constructs 列表，返回分类结果

    POST /constructs/map/
    {
      "user_id": 1,
      "entity_id": 10,
      "force": true
    }
    """
    try:
        data = json.loads(request.body)
        entity_id = data.get("entity_id")
        user_id = data.get("user_id")
        force = data.get("force", False)  # 如果 entity 已经有 construct # 不覆盖


        user = SystemUser.objects.get(pk=user_id)
        entity = Entity.objects.get(pk=entity_id)
        entity_name = entity.name
        sentence = entity.sentence
        sentence_text = entity.sentence.text

        if entity.construct and not force:
            return JsonResponse({
                "construct": entity.construct.name,
                "message": "Entity already has a construct. Set 'force': true to override."
            }, status=200)


        constructs_queryset = Construct.objects.filter(user=user)

        if not constructs_queryset:
            return JsonResponse({"error": "please upload the constructs first"})

        constructs = [
            {
                "id": c.pk,
                "name": c.name,
                "definition": c.definition,
                "examples": c.examples if isinstance(c.examples, list) else []
            }
            for c in constructs_queryset
        ]

        # sentence = data.get("sentence")
        # constructs = data.get("constructs")

        if not (entity and sentence and constructs):
            return JsonResponse({"error": "Missing entity/sentence/constructs."}, status=400)

        # construct_name = classify_construct(entity, sentence, constructs)
        # construct_name = classify_construct(entity_name, sentence_text, constructs)
        construct = classify_construct(entity_name, sentence_text, constructs)

        if construct:
            construct_obj = Construct.objects.get(pk=construct['id'])
            entity.construct = construct_obj
            entity.save()

        return JsonResponse({"construct": construct['name']}, status=200)

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON."}, status=400)



from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
import string


def classify_construct(entity: str, sentence: str, constructs: list[dict]):
    """
    给定一个 entity 和其上下文句子，以及构念定义，返回最匹配的构念名称
    :param entity: 实体文本
    :param sentence: 所属句子
    :param constructs: 构念列表 [{"name": ..., "definition": ..., "examples": [...]}]
    :return: 构念名称，如 "Emotion"
    """

    llm = ChatOpenAI(model="gpt-4o", temperature=0)

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

    print(messages)

    try:
        response = llm(messages)
        print("response:", response)
        label = response.content.strip().lower().split("label:")[-1].strip()

        # 根据 label 映射回构念 name
        for l, c in numbered_constructs:
            if l == label:
                # return c["name"]
                return c

    except Exception as e:
        print("LLM construct classification failed:", e)

    return None





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
        user = SystemUser.objects.get(pk=user_id)
        force = data.get("force", False)

        constructs_queryset = Construct.objects.filter(user=user)
        if not constructs_queryset.exists():
            return JsonResponse({"error": "Please upload the constructs first."}, status=400)

        constructs = [
            {
                "id": c.pk,
                "name": c.name,
                "definition": c.definition,
                "examples": c.examples if isinstance(c.examples, list) else []
            }
            for c in constructs_queryset
        ]

        # entities = Entity.objects.filter(user=user).select_related("sentence")
        entities = Entity.objects.filter(user=user)
        if not entities.exists():
            return JsonResponse({"error": "No entities found for the user."}, status=400)

        def process_entity(entity):
            try:
                if entity.construct and not force:
                    return None

                sentence_text = entity.sentence.text if entity.sentence else ""
                result = classify_construct(entity=entity.name, sentence=sentence_text, constructs=constructs)

                if result:
                    construct_obj = Construct.objects.get(pk=result['id'])
                    entity.construct = construct_obj
                    entity.save()

                    return {
                        "entity_id": entity.id,
                        "entity": entity.name,
                        "construct": result['name']
                    }
            except Exception as e:
                print(f"Error processing entity {entity.id}: {e}")
                return None

        updated = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(process_entity, entity) for entity in entities]
            for future in as_completed(futures):
                result = future.result()
                if result:
                    updated.append(result)

        return JsonResponse({"classified_entities": updated}, status=200)

    except SystemUser.DoesNotExist:
        return JsonResponse({"error": "User not found."}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON."}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)



@csrf_exempt
@require_http_methods(["POST"])
def assign_construct_to_entity(request):
    """
    手动分配 construct 给 entity，确保 entity 和 construct 属于同一个 user

    POST /constructs/assign/
    {
      "user_id": 1,
      "entity_id": 123,
      "construct_id": 456
    }
    """
    try:
        body = json.loads(request.body)
        user_id = body.get("user_id")
        entity_id = body.get("entity_id")
        construct_id = body.get("construct_id")

        if not all([user_id, entity_id, construct_id]):
            return JsonResponse({"error": "Fields 'user_id', 'entity_id', and 'construct_id' are required."}, status=400)

        user = SystemUser.objects.get(id=user_id)
        entity = Entity.objects.get(id=entity_id, user=user)
        construct = Construct.objects.get(id=construct_id, user=user)

        entity.construct = construct
        entity.save()

        return JsonResponse({
            "message": "Construct assigned successfully.",
            "entity_id": entity.id,
            "entity_name": entity.name,
            "construct_id": construct.id,
            "construct_name": construct.name,
        }, status=200)

    except SystemUser.DoesNotExist:
        return JsonResponse({"error": "User not found."}, status=404)
    except Entity.DoesNotExist:
        return JsonResponse({"error": "Entity not found for the given user."}, status=404)
    except Construct.DoesNotExist:
        return JsonResponse({"error": "Construct not found for the given user."}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON."}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)



@require_http_methods(["GET"])
def get_all_constructs_for_user(request, user_id):
    """
    获取指定 user_id 的所有 constructs，供前端选择

    GET /constructs/all/<user_id>/
    """
    try:
        user = SystemUser.objects.get(id=user_id)
        constructs = Construct.objects.filter(user=user)

        construct_list = [
            {
                "id": c.id,
                "name": c.name,
                "definition": c.definition,
                "examples": c.examples if isinstance(c.examples, list) else [],
            }
            for c in constructs
        ]

        return JsonResponse({"constructs": construct_list}, status=200)

    except SystemUser.DoesNotExist:
        return JsonResponse({"error": "User not found."}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

