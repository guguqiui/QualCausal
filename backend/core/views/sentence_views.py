from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db.models import Max
import json
from core.services.sentence_service import *

@csrf_exempt
@require_http_methods(["GET"])
def get_sentences(request, user_id):
    sentences = get_all_sentences(user_id)
    data = [{'id': s.id, 'text': s.text} for s in sentences]
    return JsonResponse(data, safe=False)

@csrf_exempt
@require_http_methods(["GET"])
def get_sentence(request, sentence_id):
    s = get_sentence_by_id(sentence_id)
    return JsonResponse({
        'id': s.id,
        'text': s.text,
        'line_number': s.line_number,          # ← 把行号也返回
    })

@csrf_exempt
@require_http_methods(["POST"])
def create_sentence_view(request, user_id):
    data = json.loads(request.body)
    s = create_sentence(data, user_id)
    return JsonResponse({'id': s.id, "line_number": s.line_number, 'message': 'Sentence created'})

@csrf_exempt
@require_http_methods(["PUT"])
def update_sentence_view(request, sentence_id):
    data = json.loads(request.body)
    s = update_sentence(sentence_id, data)
    return JsonResponse({'id': s.id, 'message': 'Sentence updated'})

@csrf_exempt
@require_http_methods(["DELETE"])
def delete_sentence_view(request, sentence_id):
    delete_sentence(sentence_id)
    return JsonResponse({'message': 'Sentence deleted'})
