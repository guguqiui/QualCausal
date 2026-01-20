"""
 @file: extract_entity_from_batch_sentences.py
 @Time    : 2025/7/6
 @Author  : Peinuan qin
 """

import json
import asyncio
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from automaticExtractionBackend.models import SystemUser, Sentence, Entity
from automaticExtractionBackend.async_views.extract_entity_view import (
    extract_entities_with_llm,
    sync_get_or_create_sentence,
    sync_save_entity_with_embedding,
    GLOBAL_THREAD_POOL,
)
from django.db import OperationalError


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

        llm = ChatOpenAI(model="gpt-4o", temperature=0)
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
