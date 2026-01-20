from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json

from core.services.triple_service import (
    get_all_triples, get_triple_by_id, create_triple,
    update_triple, delete_triple
)

@csrf_exempt
@require_http_methods(["GET"])
def get_triples(request, user_id):
    """获取指定用户的所有 triples"""
    triples = get_all_triples(user_id)
    data = []
    for t in triples:
        data.append({
            'id': t.id,
            'sentence_id': t.sentence.id,
            'entity_cause_id': t.entity_cause.id,
            'entity_effect_id': t.entity_effect.id
        })
    return JsonResponse(data, safe=False)

@csrf_exempt
@require_http_methods(["GET"])
def get_triple(request, triple_id):
    """获取单个 triple"""
    t = get_triple_by_id(triple_id)
    data = {
        'id': t.id,
        'sentence_id': t.sentence.id,
        'entity_cause_id': t.entity_cause.id,
        'entity_effect_id': t.entity_effect.id
    }
    return JsonResponse(data)

@csrf_exempt
@require_http_methods(["POST"])
def create_triple_view(request, user_id):
    """创建一个 triple"""
    data = json.loads(request.body)
    t = create_triple(data, user_id)
    return JsonResponse({
        'id': t.id,
        'message': 'Triple created successfully'
    })

@csrf_exempt
@require_http_methods(["PUT"])
def update_triple_view(request, triple_id):
    """更新一个 triple"""
    data = json.loads(request.body)
    t = update_triple(triple_id, data)
    return JsonResponse({
        'id': t.id,
        'message': 'Triple updated successfully'
    })

@csrf_exempt
@require_http_methods(["DELETE"])
def delete_triple_view(request, triple_id):
    """删除一个 triple"""
    delete_triple(triple_id)
    return JsonResponse({'message': 'Triple deleted successfully'})