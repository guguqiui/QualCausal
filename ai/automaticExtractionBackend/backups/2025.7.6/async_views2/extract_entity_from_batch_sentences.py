"""
 @file: extract_entity_from_batch_sentences.py
 @Time    : 2025/7/6
 @Author  : Peinuan qin
 """

import json
import asyncio
import re

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from langchain.output_parsers import ResponseSchema, StructuredOutputParser
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from concurrent.futures import ThreadPoolExecutor

from automaticExtractionBackend import settings
from automaticExtractionBackend.models import SystemUser, Sentence, Entity
# from automaticExtractionBackend.async_views.extract_entity_view import (
#     extract_entities_with_llm,
#     sync_get_or_create_sentence,
#     sync_save_entity_with_embedding,
#     GLOBAL_THREAD_POOL,
# )

from django.db import OperationalError

from automaticExtractionBackend.settings import OPENAI_KEYS

import itertools


# 全局线程池
GLOBAL_THREAD_POOL = ThreadPoolExecutor(max_workers=500)
# Assuming OPENAI_KEYS is a list of API keys
api_key_cycle = itertools.cycle(OPENAI_KEYS)  # Create an infinite cycle iterator

def get_llm_instance(max_retries=3) -> ChatOpenAI:
    """
    Get a new LLM instance based on the user_id, cycling through the API keys to balance the usage.
    """
    if not OPENAI_KEYS:
        raise ValueError("No OpenAI API keys configured")

    # Get the next available API key in the cycle (this will not repeat the same key until all have been used)
    selected_key = next(api_key_cycle)

    # Log the selection of the API key for debugging purposes
    print(f"Selecting API key: {selected_key}")

    llm = ChatOpenAI(
        openai_api_key=selected_key,
        model="gpt-4o",
        temperature=0,
        max_retries=max_retries,
        timeout=120)  # Increased timeout for robustness
    return llm







def extract_json_from_markdown(text):
    match = re.search(r"```json(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()


async def extract_entities_with_llm(llm, sentence, research_overview):
    response_schemas = [
        ResponseSchema(name="indicators", description="A a list of extracted grounded theory indicators")
    ]
    parser = StructuredOutputParser.from_response_schemas(response_schemas)
    format_instructions = parser.get_format_instructions()

    # print("format instructions:", format_instructions)
    INDICATOR_PROMPT_TEMPLATE = f"""
    Extract meaningful indicators from the provided sentence, which is taken from a qualitative data interview transcript. In grounded theory, an indicator refers to a word, phrase, or sentence, or a series of words, phrases, or sentences, in the materials being analyzed. Use the research overview as context to guide your extraction. Try to preserve subjects when extracting indicators.

    [Research Overview]
    {research_overview}

    [Sentence]
    {sentence}

    [Output Format]
    {format_instructions}
    """

    prompt = INDICATOR_PROMPT_TEMPLATE  # 不再 .format(...)

    # print("prompt:", prompt)

    messages = [
        SystemMessage(content="You are an expert in qualitative research and grounded theory analysis."),
        HumanMessage(content=prompt),
    ]

    try:
        response = await llm.agenerate([messages])

        response_text = response.generations[0][0].text.strip()

        try:
            clean_json = extract_json_from_markdown(response_text)
            result = parser.parse(clean_json)
            # print("indicators extracted: ", result.get("indicators"))
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




async def extract_entities_batch(request):
    if request.method != "POST":
        return JsonResponse({"error": "Only POST supported."}, status=405)

    try:
        data = json.loads(request.body)
        user_id = data.get("user_id")
        research_overview = data.get("research_overview", "")
        sentence_list = data.get("sentences", [])

        if not user_id or not research_overview or not sentence_list:
            return JsonResponse(
                {"error": "Missing user_id, research_overview, or sentences."}, status=400
            )

        try:
            user = await asyncio.to_thread(SystemUser.objects.get, pk=user_id)
        except SystemUser.DoesNotExist:
            return JsonResponse({"error": "User not found."}, status=404)

        # llm = ChatOpenAI(model="gpt-4o", temperature=0)
        llm = get_llm_instance()
        embedder = OpenAIEmbeddings(model="text-embedding-3-small")

        async def process_one(sentence_item):
            sentence_text = sentence_item.get("sentence")
            line_number = sentence_item.get("line_number", 1)

            if not sentence_text:
                return {"error": "Empty sentence", "line_number": line_number}

            indicators = await extract_entities_with_llm(llm, sentence_text, research_overview)
            sentence_obj = await asyncio.to_thread(
                sync_get_or_create_sentence, sentence_text, user, line_number
            )
            tasks = [
                asyncio.get_event_loop().run_in_executor(
                    GLOBAL_THREAD_POOL,
                    sync_save_entity_with_embedding,
                    ent, user, sentence_obj, embedder
                )
                for ent in indicators
            ]
            saved_entities = await asyncio.gather(*tasks, return_exceptions=True)
            filtered = [e for e in saved_entities if isinstance(e, dict)]

            return {
                "sentence": sentence_text,
                "line_number": line_number,
                "entities": filtered,
            }

        results = await asyncio.gather(
            *[process_one(item) for item in sentence_list], return_exceptions=True
        )

        return JsonResponse({"results": results}, status=200)

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON."}, status=400)
    except OperationalError:
        return JsonResponse({"error": "Database error."}, status=503)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
