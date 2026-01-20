from django.views.decorators.http import require_http_methods
from core.services.construct_service import *
import json
import requests
from core.utils.http import session
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from visualizationBackendProject.settings import API_BASE

# API_BASE = "http://ec2-18-143-66-195.ap-southeast-1.compute.amazonaws.com"
# API_BASE = "http://localhost:8001"

@csrf_exempt
@require_http_methods(["GET"])
def get_constructs(request, user_id):
    constructs = get_all_constructs(user_id)
    data = [{'id': c.id, 'name': c.name, 'definition': c.definition, 'examples': c.examples, 'color': c.color} for c in constructs]
    return JsonResponse(data, safe=False)

@csrf_exempt
@require_http_methods(["GET"])
def get_construct(request, construct_id):
    c = get_construct_by_id(construct_id)
    return JsonResponse({'id': c.id, 'name': c.name, 'definition': c.definition, 'examples': c.examples, 'color': c.color})

@csrf_exempt
@require_http_methods(["POST"])
def create_construct_view(request, user_id):
    data = json.loads(request.body)
    c = create_construct(data, user_id)
    return JsonResponse({'id': c.id, 'message': 'Construct created'})

@csrf_exempt
@require_http_methods(["PUT"])
def update_construct_view(request, construct_id):
    data = json.loads(request.body)
    c = update_construct(construct_id, data)
    return JsonResponse({'id': c.id, 'message': 'Construct updated'})

@csrf_exempt
@require_http_methods(["DELETE"])
def delete_construct_view(request, construct_id):
    delete_construct(construct_id)
    return JsonResponse({'message': 'Construct deleted'})


@csrf_exempt
def assign_construct(request):
    """
    本地 POST /api/constructs/assign/
    透传给 远端 POST /constructs/assign/
    """
    if request.method != "POST":
        return HttpResponseBadRequest("只支持 POST")

    # 直接把 body 原样拿过来
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return HttpResponseBadRequest("无效的 JSON")

    remote_url = f"{API_BASE}/constructs/assign/"

    # —— 调试打印 ——
    print("[assign_construct] Forwarding to remote:")
    print("URL:    ", remote_url)
    print("PAYLOAD:", json.dumps(payload, ensure_ascii=False))
    # 调用远端

    resp = requests.post(
        remote_url,
        json=payload,
        timeout=15
    )

    print("▶▶▶ [assign_construct] Remote response status:", resp.status_code)
    print("▶▶▶ [assign_construct] Remote response text:\n", resp.text)

    # 直接把远端返回的 JSON 和状态码原样返回
    try:
        data = resp.json()
    except ValueError:
        return JsonResponse(
            {"error": "远端返回非 JSON", "raw": resp.text},
            status=502
        )
    return JsonResponse(data, status=resp.status_code)


def list_constructs(request, user_id):
    """
    本地 GET /api/constructs/all/<user_id>/
    透传给 远端 GET /constructs/all/<user_id>/
    """
    if request.method != "GET":
        return HttpResponseBadRequest("只支持 GET")

    resp = requests.get(
        f"{API_BASE}/constructs/all/{user_id}/",
        timeout=500
    )

    try:
        data = resp.json()
    except ValueError:
        return JsonResponse(
            {"error": "远端返回非 JSON", "raw": resp.text},
            status=502
        )
    return JsonResponse(data, status=resp.status_code)

@csrf_exempt
def update_construct(request, id):
    """
    POST /api/constructs/update/<id>/
    透传给远端 POST {API_BASE}/constructs/update/<id>/
    """
    if request.method != "POST":
        return HttpResponseBadRequest("只支持 POST")
    try:
        payload = json.loads(request.body.decode())
    except Exception:
        return HttpResponseBadRequest("无效 JSON")

    print(payload)
    target_url = f"{API_BASE}/constructs/update/{id}/"
    resp = requests.post(
        target_url,
        json=payload,
        timeout=50
    )

    try:
        data = resp.json()
    except ValueError:
        return JsonResponse({"error":"远端未返回 JSON"}, status=502)
    return JsonResponse(data, status=resp.status_code)

@csrf_exempt
def delete_construct(request, id):
    """
    POST /api/constructs/delete/<id>/
    透传给远端 POST {API_BASE}/constructs/delete/<id>/
    """
    if request.method != "POST":
        return HttpResponseBadRequest("只支持 POST")
    resp = requests.post(
        f"{API_BASE}/constructs/delete/{id}/",
        timeout=15
    )
    try:
        data = resp.json()
    except ValueError:
        return JsonResponse({"error":"远端未返回 JSON"}, status=502)
    return JsonResponse(data, status=resp.status_code)