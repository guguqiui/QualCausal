"""
 @file: resolution_patch_view.py
 @Time    : 2025/4/10
 @Author  : Peinuan qin
 """
import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
import concurrent.futures
from automaticExtractionBackend.models import SystemUser, Entity, Triple
from automaticExtractionBackend.settings import EMBEDDING_MODELS

@csrf_exempt
@require_http_methods(["POST"])
def auto_entity_resolution(request):
    from scipy.spatial.distance import cosine
    from collections import defaultdict

    data = json.loads(request.body)
    user_id = data.get("user_id")
    k = data.get("k", 10)
    max_workers = data.get("max_workers", 10)  # 🌟 支持传入并发数，不传的话默认10个线程

    user = SystemUser.objects.get(pk=user_id)
    entities = Entity.objects.filter(user=user)

    id_to_entity = {str(e.id): e for e in entities if e.embeddings}
    all_ids = list(id_to_entity.keys())
    all_embeddings = {
        eid: e.embeddings for eid, e in id_to_entity.items()
    }

    # Step 1: 构建相似实体对集合
    combined_pairs = set()
    for model_name in EMBEDDING_MODELS:
        for i in range(len(all_ids)):
            eid1 = all_ids[i]
            vec1 = all_embeddings[eid1].get(model_name)
            if not vec1:
                continue

            scores = []
            for j in range(len(all_ids)):
                if i == j:
                    continue
                eid2 = all_ids[j]
                vec2 = all_embeddings[eid2].get(model_name)
                if not vec2:
                    continue

                dist = cosine(vec1, vec2)
                scores.append((dist, tuple(sorted([eid1, eid2]))))

            topk = sorted(scores)[:k]
            combined_pairs.update([pair for _, pair in topk])

    # Step 2: LLM并发判断是否同义 ✅
    uf = UnionFind()
    confirmed = []

    tasks = []
    for eid1, eid2 in combined_pairs:
        e1 = id_to_entity[eid1]
        e2 = id_to_entity[eid2]

        if e1.construct_id != e2.construct_id:
            continue

        sent1 = e1.sentence.text if e1.sentence else ""
        sent2 = e2.sentence.text if e2.sentence else ""

        tasks.append((e1, sent1, e2, sent2))

    def judge_equivalent(task):
        e1, sent1, e2, sent2 = task
        try:
            if ask_llm_if_equivalent(e1.name, sent1, e2.name, sent2):
                return (e1.id, e2.id, e1.name, e2.name)
        except Exception as e:
            print(f"LLM call failed for {e1.name} & {e2.name}: {e}")
        return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(judge_equivalent, tasks))

    for res in results:
        if res:
            eid1, eid2, name1, name2 = res
            uf.union(eid1, eid2)
            confirmed.append((name1, name2))

    # Step 3 ~ Step 5：不变
    cluster_map = defaultdict(list)
    for e in entities:
        cluster_map[uf.find(e.id)].append(e.id)

    entity_map = {}
    for cluster in cluster_map.values():
        kept = min(cluster)
        for eid in cluster:
            entity_map[eid] = kept

    updated_canonicals = []
    for eid, kept_id in entity_map.items():
        if eid == kept_id:
            continue
        try:
            entity = Entity.objects.get(id=eid)
            canonical = Entity.objects.get(id=kept_id)
            entity.canonical_entity = canonical
            entity.save()
            updated_canonicals.append((eid, kept_id))
        except Entity.DoesNotExist:
            continue

    updated_triples = []
    for triple in Triple.objects.filter(user=user):
        updated = False
        if triple.entity_cause.canonical_entity:
            triple.entity_cause = triple.entity_cause.canonical_entity
            updated = True
        if triple.entity_effect.canonical_entity:
            triple.entity_effect = triple.entity_effect.canonical_entity
            updated = True
        if updated:
            triple.save()
            updated_triples.append(triple.id)

    return JsonResponse({
        "merged_pairs": confirmed,
        "updated_canonical_map": updated_canonicals,
        "updated_triples": updated_triples
    }, status=200)


class UnionFind:
    def __init__(self):
        self.parent = {}

    def find(self, item):
        if item not in self.parent:
            self.parent[item] = item
        if self.parent[item] != item:
            self.parent[item] = self.find(self.parent[item])
        return self.parent[item]

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra


def ask_llm_if_equivalent(entity1, sentence1, entity2, sentence2):

    LLM_PROMPT = """
Step 4: entity resolution
# Knowledge Graph Entity Resolution

Determine if Entity 1 and Entity 2 represent the same real-world concept or refer to functionally identical semantic meanings despite different surface forms. Entities should ONLY be merged if they are equivalents, not merely related or similar concepts. For merging to be appropriate, the entities need to be interchangeable in their respective contexts without changing the meaning.

[Example 1]
Entity 1: needs to seek advice and support with medical or otherwise
Context: No not at all. Avery has a mental health condition that he needs to seek advice and support with medical or otherwise. Avery should make an appointment and go and see his GP.

Entity 2: needs to seek help
Context: Definitely. Avery is not a bad or harmful person. She just needs to seek help and have a great support structure around her. The fact that she has the capability to seek employment for me shows that she is determined to live a fulfilling life.

Answer: Yes (These entities represent the same semantic concept of "seeking professional assistance for mental health" despite surface form differences)

[Example 2]
Entity 1: should make an appointment and go and see GP
Context: No not at all. Avery has a mental health condition that he needs to seek advice and support with medical or otherwise. Avery should make an appointment and go and see his GP.

Entity 2: should have kept calm
Context: In a way yes they should understand Avery's situation. They should have kept calm and helped Avery to cool down.

Answer: No

[Input]
Entity 1: [entity 1]
Context: [context 1]

Entity 2: [entity 2]
Context: [context 2]

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
