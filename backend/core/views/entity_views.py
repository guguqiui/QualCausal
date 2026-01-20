from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
import requests

from core.services.entity_service import (
    get_all_entities, get_entity_by_id, create_entity,
    update_entity, delete_entity
)

from visualizationBackendProject.settings import API_BASE
# API_BASE = "http://ec2-18-143-66-195.ap-southeast-1.compute.amazonaws.com"

@csrf_exempt
@require_http_methods(["GET"])
def get_entities(request, user_id):
    entities = get_all_entities(user_id)
    data = [{
        'id': e.id,
        'name': e.name,
        'construct': e.construct.name if e.construct else None,
        'construct_id': e.construct.id if e.construct else None,
        'sentence_id': e.sentence.id if e.sentence else None,
        'embeddings': e.embeddings,
        'canonical_entity_id': e.canonical_entity.id if e.canonical_entity else None
    } for e in entities]
    return JsonResponse(data, safe=False)

@csrf_exempt
@require_http_methods(["GET"])
def get_entities_by_name(request, user_id, node_name):
    """
    根据节点名称过滤返回 entity。
    假设这里返回当前用户下所有名字为 node_name 的 entity
    """
    entities = get_all_entities(user_id)
    # 根据实体名称过滤（注意：过滤时注意大小写、前后空格等问题，可根据实际需求调整）
    filtered = [e for e in entities if e.name == node_name]
    data = [{
        'id': e.id,
        'name': e.name,
        'construct': e.construct.name if e.construct else None,
        'sentence_id': e.sentence.id if e.sentence else None,
        'embeddings': e.embeddings,
        'canonical_entity_id': e.canonical_entity.id if e.canonical_entity else None
    } for e in filtered]
    return JsonResponse(data, safe=False)

@csrf_exempt
@require_http_methods(["GET"])
def get_entity(request, entity_id):
    entity = get_entity_by_id(entity_id)
    data = {
        'id': entity.id,
        'name': entity.name,
        'construct': entity.construct.name if entity.construct else None,
        'sentence_id': entity.sentence.id if entity.sentence else None,
        'embeddings': entity.embeddings,
        'canonical_entity_id': entity.canonical_entity.id if entity.canonical_entity else None
    }
    return JsonResponse(data)

@csrf_exempt
@require_http_methods(["POST"])
def create_entity_view(request, user_id):
    data = json.loads(request.body)
    entity = create_entity(data, user_id)
    return JsonResponse({'id': entity.id, 'message': 'Entity created successfully'})

@csrf_exempt
@require_http_methods(["PUT"])
def update_entity_view(request, entity_id):
    data = json.loads(request.body)
    entity = update_entity(entity_id, data)
    return JsonResponse({'id': entity.id, 'message': 'Entity updated successfully'})

@csrf_exempt
@require_http_methods(["DELETE"])
def delete_entity_view(request, entity_id):
    delete_entity(entity_id)
    return JsonResponse({'message': 'Entity deleted successfully'})

@csrf_exempt
@require_http_methods(["POST"])
def update_entity_name_view(request):
    # 1. 解析 JSON
    try:
        data = json.loads(request.body.decode())
    except json.JSONDecodeError:
        return HttpResponseBadRequest("Invalid JSON")

    entity_id = data.get("entity_id")
    new_name  = data.get("new_name")
    if not entity_id or not new_name:
        return JsonResponse(
            {"error": "entity_id and new_name are required."},
            status=400
        )

    # 2. 转发给远端 API
    try:
        resp = requests.post(
            f"{API_BASE}/update_entity_name/",
            json={"entity_id": entity_id, "new_name": new_name},
            timeout=10
        )
    except requests.RequestException as e:
        return JsonResponse(
            {"error": f"Failed to reach remote service: {e}"},
            status=502
        )

    # 3. 检查远端返回状态
    if resp.status_code != 200:
        # 如果远端返回了 JSON 错误消息，就透传
        try:
            return JsonResponse(resp.json(), status=resp.status_code)
        except ValueError:
            return JsonResponse(
                {"error": f"Remote service returned status {resp.status_code}"},
                status=resp.status_code
            )

    # 4. 成功则把远端的 JSON 原样返回
    return JsonResponse(resp.json(), status=200)

@csrf_exempt
@require_http_methods(["POST"])
def delete_entity(request):
    """
    接收前端 POST /api/delete_entity/
    Body: { "entity_id": 123, "user_id": 456 }
    然后转发给远端的 DELETE 接口。
    """
    # 1. 解析入参
    try:
        payload = json.loads(request.body.decode())
        entity_id = payload["entity_id"]
        user_id   = payload["user_id"]
    except (json.JSONDecodeError, KeyError):
        return HttpResponseBadRequest("请求体需要 JSON 且包含 entity_id, user_id")

    # 2. 转发到远端
    try:
        resp = requests.post(
            f"{API_BASE}/delete_entity/",
            json={"entity_id": entity_id, "user_id": user_id},
            timeout=10
        )
    except requests.RequestException as e:
        return JsonResponse({"error": f"无法访问远端服务: {e}"}, status=502)

    # 3. 透传远端返回
    if resp.status_code != 200:
        try:
            return JsonResponse(resp.json(), status=resp.status_code)
        except ValueError:
            return JsonResponse(
                {"error": f"远端服务返回状态 {resp.status_code}"},
                status=resp.status_code
            )

    return JsonResponse(resp.json(), status=200)