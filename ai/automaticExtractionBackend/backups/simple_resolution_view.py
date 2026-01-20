# """
#  @file: simple_resolution_view.py
#  @Time    : 2025/4/5
#  @Author  : Peinuan qin
#
#  这个只用 openai 的 embedding 而不是多个 model 的 union 来产生候选合并的 entities
#  """
#
# import json
# from concurrent.futures import ThreadPoolExecutor, as_completed
# from django.http import JsonResponse
# from django.views.decorators.csrf import csrf_exempt
# from django.views.decorators.http import require_http_methods
# from scipy.spatial.distance import cosine
#
# from automaticExtractionBackend import settings
# from automaticExtractionBackend.models import SystemUser, Entity, Triple
# from langchain_core.messages import SystemMessage, HumanMessage
# from langchain_openai import ChatOpenAI
#
#
#
# @csrf_exempt
# @require_http_methods(["POST"])
# def auto_entity_resolution(request):
#     data = json.loads(request.body)
#     user_id = data.get("user_id")
#     k = data.get("k", 10)
#
#     user = SystemUser.objects.get(pk=user_id)
#     entities = Entity.objects.filter(user=user)
#
#     embedding_model_name = settings.EMBEDDING_MODEL
#
#     # 只保留有 openai embedding 的实体
#     # valid_entities = [e for e in entities if e.embeddings and e.embeddings.get("openai")]
#     valid_entities = [e for e in entities if e.embeddings and e.embeddings.get(embedding_model_name)]
#     id_to_entity = {e.id: e for e in valid_entities}
#     all_ids = list(id_to_entity.keys())
#
#     # 构建候选对集合（每个 entity 和其他最相似的 k 个）
#     candidate_pairs = set()
#     for i in range(len(all_ids)):
#         eid1 = all_ids[i]
#         # vec1 = id_to_entity[eid1].embeddings["openai"]
#         vec1 = id_to_entity[eid1].embeddings[embedding_model_name]
#
#         scores = []
#         for j in range(len(all_ids)):
#             if i == j:
#                 continue
#             eid2 = all_ids[j]
#             # vec2 = id_to_entity[eid2].embeddings["openai"]
#             vec2 = id_to_entity[eid2].embeddings[embedding_model_name]
#             dist = cosine(vec1, vec2)
#             scores.append((dist, tuple(sorted((eid1, eid2)))))
#
#         topk = sorted(scores)[:k]
#         candidate_pairs.update([pair for _, pair in topk])
#
#     # 使用线程池并发判断等价
#     confirmed = []
#     removed_ids = set()
#     updated_triples = []
#
#     def resolve_pair(pair):
#         eid1, eid2 = pair
#         e1 = id_to_entity[eid1]
#         e2 = id_to_entity[eid2]
#         sent1 = e1.sentence.text if e1.sentence else ""
#         sent2 = e2.sentence.text if e2.sentence else ""
#
#         if ask_llm_if_equivalent(e1.name, sent1, e2.name, sent2):
#             return pair
#         return None
#
#     with ThreadPoolExecutor(max_workers=5) as executor:
#         future_to_pair = {executor.submit(resolve_pair, pair): pair for pair in candidate_pairs}
#         for future in as_completed(future_to_pair):
#             result = future.result()
#             if result:
#                 eid1, eid2 = result
#                 e1, e2 = id_to_entity[eid1], id_to_entity[eid2]
#                 kept, removed = (eid1, eid2) if eid1 < eid2 else (eid2, eid1)
#                 # for triple in Triple.objects.filter(user=user):
#                 #     changed = False
#                 #     if triple.start_entity_id == removed:
#                 #         triple.start_entity_id = kept
#                 #         changed = True
#                 #     if triple.end_entity_id == removed:
#                 #         triple.end_entity_id = kept
#                 #         changed = True
#                 #     if changed:
#                 #         triple.save()
#                 #         updated_triples.append(triple.id)
#
#                 for triple in Triple.objects.filter(user=user):
#                     changed = False
#                     if triple.entity_cause_id == removed:
#                         triple.entity_cause_id = kept
#                         changed = True
#                     if triple.entity_effect_id == removed:
#                         triple.entity_effect_id = kept
#                         changed = True
#                     if changed:
#                         triple.save()
#                         updated_triples.append(triple.id)
#
#                 Entity.objects.filter(id=removed).delete()
#                 removed_ids.add(removed)
#                 confirmed.append((e1.name, e2.name))
#
#     return JsonResponse({
#         "merged_pairs": confirmed,
#         "removed_entity_ids": list(removed_ids),
#         "updated_triples": updated_triples
#     }, status=200)
#
#
# def ask_llm_if_equivalent(entity1, sentence1, entity2, sentence2):
#     LLM_PROMPT = """
# Step 4: Entity Resolution
# Are the two entities Entity 1 and Entity 2 referring to the same thing, based on their respective contexts? Answer yes or no.
#
# Entity 1 Context: Sentence 1
# Entity 2 Context: Sentence 2
#
# Only return "yes" or "no".
#     """
#     messages = [
#         SystemMessage(content=LLM_PROMPT),
#         HumanMessage(content=f"""
# Entity 1: {entity1}
# Sentence 1: {sentence1}
#
# Entity 2: {entity2}
# Sentence 2: {sentence2}
# """)
#     ]
#
#     llm = ChatOpenAI(model="gpt-4o", temperature=0)
#     try:
#         response = llm.invoke(messages).content.strip().lower()
#         return response == "yes"
#     except Exception as e:
#         print(f"LLM failed: {e}")
#         return False







import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db import transaction
from scipy.spatial.distance import cosine

from automaticExtractionBackend import settings
from automaticExtractionBackend.models import SystemUser, Entity, Triple
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from django.db.models import Q



@csrf_exempt
@require_http_methods(["POST"])
def auto_entity_resolution(request):
    data = json.loads(request.body)
    user_id = data.get("user_id")
    k = data.get("k", 10)

    user = SystemUser.objects.get(pk=user_id)
    entities = Entity.objects.filter(user=user)

    embedding_model_name = settings.EMBEDDING_MODEL

    valid_entities = [e for e in entities if e.embeddings and e.embeddings.get(embedding_model_name)]
    id_to_entity = {e.id: e for e in valid_entities}
    all_ids = list(id_to_entity.keys())

    # 生成候选对（每个 entity 和最相似的 k 个）
    candidate_pairs = set()
    for i in range(len(all_ids)):
        eid1 = all_ids[i]
        vec1 = id_to_entity[eid1].embeddings[embedding_model_name]

        scores = []
        for j in range(len(all_ids)):
            if i == j:
                continue
            eid2 = all_ids[j]
            vec2 = id_to_entity[eid2].embeddings[embedding_model_name]
            dist = cosine(vec1, vec2)
            scores.append((dist, tuple(sorted((eid1, eid2)))))

        topk = sorted(scores)[:k]
        candidate_pairs.update([pair for _, pair in topk])

    confirmed = []
    removed_ids = set()
    updated_triples = []

    def resolve_pair(pair):
        eid1, eid2 = pair
        e1 = id_to_entity[eid1]
        e2 = id_to_entity[eid2]
        sent1 = e1.sentence.text if e1.sentence else ""
        sent2 = e2.sentence.text if e2.sentence else ""

        if ask_llm_if_equivalent(e1.name, sent1, e2.name, sent2):
            return pair
        return None

    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_pair = {executor.submit(resolve_pair, pair): pair for pair in candidate_pairs}
        for future in as_completed(future_to_pair):
            result = future.result()
            if result:
                eid1, eid2 = result
                e1, e2 = id_to_entity[eid1], id_to_entity[eid2]
                kept, removed = (eid1, eid2) if eid1 < eid2 else (eid2, eid1)

                try:
                    with transaction.atomic():
                        # 更新所有 triples 中的引用
                        triples = Triple.objects.filter(user=user).filter(
                            Q(entity_cause_id=removed) | Q(entity_effect_id=removed)
                        )
                        for triple in triples:
                            changed = False
                            if triple.entity_cause_id == removed:
                                triple.entity_cause_id = kept
                                changed = True
                            if triple.entity_effect_id == removed:
                                triple.entity_effect_id = kept
                                changed = True
                            if changed:
                                triple.save()
                                updated_triples.append(triple.id)

                        # 删除被合并的 entity
                        Entity.objects.filter(id=removed).delete()

                        removed_ids.add(removed)
                        confirmed.append((e1.name, e2.name))
                except Exception as e:
                    print(f"Failed to merge entity {eid1} and {eid2}: {e}")

    return JsonResponse({
        "merged_pairs": confirmed,
        "removed_entity_ids": list(removed_ids),
        "updated_triples": updated_triples
    }, status=200)


def ask_llm_if_equivalent(entity1, sentence1, entity2, sentence2):
    LLM_PROMPT = """
Step 4: Entity Resolution
Are the two entities Entity 1 and Entity 2 referring to the same thing, based on their respective contexts? Answer yes or no.

Entity 1 Context: Sentence 1
Entity 2 Context: Sentence 2

Only return "yes" or "no".
    """
    messages = [
        SystemMessage(content=LLM_PROMPT),
        HumanMessage(content=f"""
Entity 1: {entity1}
Sentence 1: {sentence1}

Entity 2: {entity2}
Sentence 2: {sentence2}
""")
    ]

    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    try:
        response = llm.invoke(messages).content.strip().lower()
        return response == "yes"
    except Exception as e:
        print(f"LLM failed: {e}")
        return False
