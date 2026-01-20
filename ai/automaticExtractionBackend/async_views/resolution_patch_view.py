import json
from concurrent.futures import ThreadPoolExecutor
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from collections import defaultdict
from scipy.spatial.distance import cosine
from automaticExtractionBackend.models import SystemUser, Entity, Triple
from automaticExtractionBackend.settings import EMBEDDING_MODELS, OPENAI_KEYS
import logging
import asyncio
import nest_asyncio
nest_asyncio.apply()
# Global thread pool (singleton pattern)
# GLOBAL_THREAD_POOL = ThreadPoolExecutor(max_workers=200)  # Adjust based on server configuration
GLOBAL_THREAD_POOL = ThreadPoolExecutor(max_workers=300)  # Adjust based on server configuration
logger = logging.getLogger(__name__)


BATCH_SIZE = 10
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

import itertools

# Assuming OPENAI_KEYS is a list of API keys
api_key_cycle = itertools.cycle(OPENAI_KEYS)  # Create an infinite cycle iterator

def get_random_llm_instance(user_id, max_retries=3) -> ChatOpenAI:
    """
    Get a new LLM instance based on the user_id, cycling through the API keys to balance the usage.
    """
    if not OPENAI_KEYS:
        raise ValueError("No OpenAI API keys configured")

    # Get the next available API key in the cycle (this will not repeat the same key until all have been used)
    selected_key = next(api_key_cycle)

    # Log the selection of the API key for debugging purposes
    logger.debug(f"Selecting API key: {selected_key} for user_id: {user_id}")

    llm = ChatOpenAI(
        openai_api_key=selected_key,
        model="gpt-4o",
        temperature=0,
        max_retries=max_retries,
        timeout=120)  # Increased timeout for robustness
    print(f"Created new LLM instance for user_id: {user_id} using API key: sk-{selected_key[-5:]}")
    return llm


LLM_PROMPT = """
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

The final output only needs the string "yes" or "no"; 
no other characters should be included!!
"""

async def ask_llm_if_equivalent_batch_async(llm: ChatOpenAI, prompts, messages_lst, batch_size=25):
    results = []
    try:
        # Split prompts into smaller batches
        for i in range(0, len(prompts), batch_size):
            prompt_batch = prompts[i:i + batch_size]
            message_batch = messages_lst[i:i + batch_size]

            # Send batch requests using agenerate
            response = await llm.agenerate(message_batch)

            # Process results for each batch
            for generation_list, (e1, sent1, e2, sent2, prompt_text) in zip(response.generations, prompt_batch):
                for generation in generation_list:
                    result = {
                        "e1": e1,
                        "e2": e2,
                        "resolution": generation.text.strip().lower() == 'yes'
                    }
                    results.append(result)

        return results
    except Exception as e:
        logger.error(f"LLM failed: {e}")
        return []


def sync_wrapper(args):
    """Sync wrapper for thread pool to execute async functions"""
    try:
        # Each thread uses an independent event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(ask_llm_if_equivalent_batch_async(*args))
    except Exception as e:
        logger.error(f"Thread processing failed: {e}")
        return []
    finally:
        if loop:
            loop.close()


@csrf_exempt
@require_http_methods(["POST"])
def auto_entity_resolution(request):
    try:
        data = json.loads(request.body)
        user_id = data.get("user_id")
        k = data.get("k", 10)

        # Get user data
        try:
            user = SystemUser.objects.get(pk=user_id)
            entities = list(Entity.objects.filter(user=user).select_related('sentence'))
        except SystemUser.DoesNotExist:
            return JsonResponse({"error": "User not found"}, status=404)

        # Prepare data
        id_to_entity = {str(e.id): e for e in entities if e.embeddings}
        all_ids = list(id_to_entity.keys())
        all_embeddings = {eid: e.embeddings for eid, e in id_to_entity.items()}

        # Step 1: Construct similar entity pair set (synchronous)
        combined_pairs = set()
        for model_name in EMBEDDING_MODELS:
            for i in range(len(all_ids)):
                eid1 = all_ids[i]
                vec1 = all_embeddings[eid1].get(model_name)
                if not vec1:
                    continue

                scores = []
                for j in range(i + 1, len(all_ids)):  # Optimization: avoid redundant calculation
                    eid2 = all_ids[j]
                    vec2 = all_embeddings[eid2].get(model_name)
                    if not vec2:
                        continue

                    dist = cosine(vec1, vec2)
                    scores.append((dist, (eid1, eid2)))

                topk = sorted(scores)[:k]
                combined_pairs.update([pair for _, pair in topk])

        # Step 2: LLM concurrent judgment
        uf = UnionFind()
        confirmed = []

        # Prepare tasks and batch them
        tasks = []
        for eid1, eid2 in combined_pairs:
            e1 = id_to_entity[eid1]
            e2 = id_to_entity[eid2]

            if e1.construct_id != e2.construct_id:
                continue

            sent1 = e1.sentence.text if e1.sentence else ""
            sent2 = e2.sentence.text if e2.sentence else ""
            tasks.append((e1, sent1, e2, sent2))

        # Create prompts and messages_lst
        prompts = []
        for task in tasks:
            e1, sent1, e2, sent2 = task
            prompt_text = f"""
            Entity 1: {e1}
            Sentence 1: {sent1}

            Entity 2: {e2}
            Sentence 2: {sent2}
            """
            prompts.append((e1, sent1, e2, sent2, prompt_text))

        messages_lst = [
            [SystemMessage(content=LLM_PROMPT), HumanMessage(content=prompt_text)]
            for _, _, _, _, prompt_text in prompts
        ]

        # Use ThreadPoolExecutor to submit tasks and batch them
        batch_size = BATCH_SIZE  # Adjust batch size based on your server's capabilities
        results = []

        try:
            # Split prompts into batches
            futures = []
            for i in range(0, len(prompts), batch_size):
                batch_prompts = prompts[i:i + batch_size]
                batch_messages_lst = messages_lst[i:i + batch_size]

                # Submit each batch as a separate task to the thread pool
                futures.append(GLOBAL_THREAD_POOL.submit(sync_wrapper, (
                get_random_llm_instance(user_id), batch_prompts, batch_messages_lst)))

            # Wait for all futures to complete
            for future in futures:
                result = future.result(timeout=300)  # Set timeout
                if result:
                    results.extend(result)

        except Exception as e:
            logger.error(f"Thread pool error: {e}")

        # Collect confirmed results
        for result in results:
            if result["resolution"]:
                e1_id, e2_id = result["e1"].id, result["e2"].id
                uf.union(e1_id, e2_id)
                confirmed.append((result["e1"].name, result["e2"].name))

        # Further processing (remains unchanged)
        cluster_map = defaultdict(list)
        for e in entities:
            cluster_map[uf.find(e.id)].append(e.id)

        entity_map = {}
        for cluster in cluster_map.values():
            kept = min(cluster)
            for eid in cluster:
                entity_map[eid] = kept

        # Batch update database for canonical entities
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

        # Batch update triples for canonical entities
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
                # triple.save()
                # updated_triples.append(triple.id)

                if not Triple.objects.filter(
                        user=user,
                        sentence=triple.sentence,
                        entity_cause=triple.entity_cause,
                        entity_effect=triple.entity_effect
                ).exists():
                    # 如果没有重复，保存新的 Triple
                    triple.save()
                    updated_triples.append(triple.id)
                else:
                    # 如果已经存在，跳过或记录
                    logger.warning(
                        f"Triple already exists: user={user.id}, sentence={triple.sentence.id}, cause={triple.entity_cause.id}, effect={triple.entity_effect.id}")

        return JsonResponse({
            "merged_pairs": confirmed,
            "updated_canonical_map": updated_canonicals,
            "updated_triples": updated_triples
        }, status=200)

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        logger.exception("Unexpected error in auto_entity_resolution")
        return JsonResponse({"error": str(e)}, status=500)
