import json
import asyncio
from concurrent.futures import ThreadPoolExecutor
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from automaticExtractionBackend.models import Entity, SystemUser, Sentence
from django.db import OperationalError
from automaticExtractionBackend import settings


# 全局定义线程池
GLOBAL_THREAD_POOL = ThreadPoolExecutor(max_workers=50)  # 根据服务器CPU核心数调整


SYSTEM_PROMPT = """
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


async def extract_entities_with_llm(llm, sentence):
    """Async function to extract entities using LLM"""
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=sentence),
    ]
    try:
        response = await llm.agenerate([messages])
        response_text = response.generations[0][0].text.strip()
        return json.loads(response_text).get("entities", [])
    except Exception as e:
        print(f"[LLM Error]: {e}")
        return []


def sync_get_or_create_sentence(sentence_text, user, line_number):
    """Synchronous DB operation to be run in thread"""
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
    """Synchronous entity saving operation to be run in thread"""
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
                obj.embeddings = {"embedding-model": embedding_vector}
                obj.save()
            except Exception as e:
                print(f"[Embedding Failed] '{ent_name}': {e}")

        return {"id": obj.id, "name": obj.name}
    except Exception as e:
        print(f"[Error saving entity] '{ent_name}': {e}")
        return None


# async def process_entities(entities, user, sentence_obj, embedder, max_workers=10):
#     """Process entities in parallel using ThreadPoolExecutor； 这个版本使用的是部分线程池，下面的改成全局线程池"""
#     saved_entities = []
#
#     with ThreadPoolExecutor(max_workers=max_workers) as executor:
#         loop = asyncio.get_event_loop()
#         tasks = [
#             loop.run_in_executor(
#                 executor,
#                 sync_save_entity_with_embedding,
#                 ent, user, sentence_obj, embedder
#             )
#             for ent in entities
#         ]
#
#         results = await asyncio.gather(*tasks)
#         saved_entities.extend([r for r in results if r is not None])
#
#     return saved_entities


async def process_entities(entities, user, sentence_obj, embedder):
    """使用全局线程池"""
    tasks = [
        asyncio.get_event_loop().run_in_executor(
            GLOBAL_THREAD_POOL,
            sync_save_entity_with_embedding,
            ent, user, sentence_obj, embedder
        )
        for ent in entities
    ]
    # return [r for r in await asyncio.gather(*tasks) if r is not None]
    try:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in results:
            if isinstance(r, Exception):
                # logger.error(f"Entity processing failed: {r}")
                print("error", r)
        return [r for r in results if not isinstance(r, Exception)]
    except Exception as e:
        # logger.critical(f"Thread pool crashed: {e}")
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

            if not (sentence_text and user_id):
                return {"error": "No sentence or user_id provided."}, 400

            try:
                user = await asyncio.to_thread(SystemUser.objects.get, pk=user_id)
            except SystemUser.DoesNotExist:
                return {"error": "User not found."}, 404

            # Initialize LLM and embedder
            llm = ChatOpenAI(model="gpt-4o", temperature=0)
            embedder = OpenAIEmbeddings(model=settings.EMBEDDING_MODEL)

            # Extract entities with LLM
            entities = await extract_entities_with_llm(llm, sentence_text)

            # Get or create sentence in a thread
            sentence_obj = await asyncio.to_thread(
                sync_get_or_create_sentence,
                sentence_text, user, line_number
            )

            # Process entities in parallel
            saved_entities = await process_entities(
                entities, user, sentence_obj, embedder
            )

            return {"entities": saved_entities}, 200

        except json.JSONDecodeError:
            return {"error": "Invalid JSON."}, 400
        except OperationalError as e:
            return {"error": "Server/database connection issue."}, 503
        except Exception as e:
            return {"error": str(e)}, 500

    # Run the async function and return response
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result, status_code = loop.run_until_complete(async_extract_entity())
        return JsonResponse(result, status=status_code)
    finally:
        loop.close()



