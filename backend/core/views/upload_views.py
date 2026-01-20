import json
import time
import logging
import requests
import certifi
from requests.exceptions import RequestException
from core.utils.http import session
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from concurrent.futures import ThreadPoolExecutor, as_completed
from visualizationBackendProject.settings import API_BASE

# API_BASE = "http://ec2-18-143-66-195.ap-southeast-1.compute.amazonaws.com"
# API_BASE = "http://ec2-13-213-43-132.ap-southeast-1.compute.amazonaws.com"
# API_BASE = "http://localhost:8001"

DEFAULT_K           = 5
DEFAULT_MAX_WORKERS = 20
logger = logging.getLogger(__name__)

def split_sentences(text: str):
    """
    按行拆分，并把行号也一并返回。
    比如传入：
      111.222
      333
    返回：
      [
        {"text": "111.222", "line_number": 1},
        {"text": "333",    "line_number": 2},
      ]
    """
    result = []
    for idx, line in enumerate(text.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        result.append({
            "text": line,
            "line_number": idx
        })
    return result

# @csrf_exempt
# def upload_entities(request):
#     """
#     功能: 上传整段文本（带行号）给远端接口做实体抽取
#     """
#     if request.method != "POST":
#         return HttpResponseBadRequest("只支持 POST")
#
#     try:
#         body    = json.loads(request.body.decode("utf-8"))
#         text    = body["text"]
#         user_id = int(body["user_id"])
#         overview = body.get("overview", "")
#     except Exception:
#         return HttpResponseBadRequest("请求体需包含 text (string) 与 user_id (int)")
#
#     # 1) 按行拆分，并把行号打包
#     sentences_with_lines = split_sentences(text)
#     results = []
#
#     def fetch_for_sentence(item):
#         """
#         item = {"text": "...", "line_number": N}
#         """
#         sent_txt = item["text"]
#         line_no  = item["line_number"]
#         ents = []
#         err = None
#
#         for attempt in range(2):
#             try:
#                 resp = requests.post(
#                     f"{API_BASE}/extract_entity/",
#                     json={
#                         "sentence": sent_txt,
#                         "user_id": user_id,
#                         "line_number": line_no, # 把行号一起传给远端
#                         "research_overview": overview
#                     },
#                     timeout=1000
#                 )
#
#                 try:
#                     payload = resp.json()
#                 except ValueError:
#                     logging.warning(f"Invalid JSON (status {resp.status_code})")
#                     logging.warning(f"[Line {line_no}] JSON parse failed: {err}")
#                     # 不是 “User not found.”，继续重试
#                     continue
#
#                 # 只有当后端明确返回了这个错误信息，才当作用户不存在
#                 if payload.get("error") == "User not found.":
#                     raise ValueError("User not found.")
#
#                 # 其余非 200 的状态都当普通失败，记录一下，重试或报错到前端
#                 if resp.status_code != 200:
#                     # err = f"Status {resp.status_code}"
#                     logging.warning(f"Status {resp.status_code}")
#                     logging.warning(f"Attempt {attempt + 1} failed: {err}")
#                     continue
#
#                 # 真正成功
#                 ents = payload.get("entities", [])
#                 err = None
#                 break
#
#             except ValueError as e:
#                 # 只有 “User not found.” 才上抛
#                 if str(e) == "User not found.":
#                     raise
#                 # 其它 ValueError 当普通失败
#                 err = str(e)
#                 logging.warning(f"ValueError: {err}")
#
#             except Exception as e:
#                 err = str(e)
#                 logging.warning(f"Attempt {attempt + 1} exception: {err}")
#
#             if attempt < 1:
#                 time.sleep(1)
#
#         # 保持一定间隔（可选）
#         time.sleep(2)
#
#         return {
#             "sentence":       sent_txt,
#             "line_number":    line_no,
#             "entities":       ents,
#             "error":          err
#         }
#
#     # 并发执行
#     try:
#         # with ThreadPoolExecutor(max_workers=5) as pool:
#         with ThreadPoolExecutor(max_workers=DEFAULT_MAX_WORKERS) as pool:
#             future_to_sent = { pool.submit(fetch_for_sentence, item): item for item in sentences_with_lines }
#             for fut in as_completed(future_to_sent):
#                 try:
#                     results.append(fut.result())
#                 except ValueError as e:
#                     if str(e) == "User not found.":
#                         return JsonResponse({"error": "User not found."}, status=404)
#     except Exception as e:
#         return JsonResponse({"error": f"Internal error: {e}"}, status=500)
#
#     # 最终把所有结果一次性返回给前端
#     return JsonResponse({"sentences": results})




@csrf_exempt
def upload_entities(request):
    """
    功能: 上传整段文本（带行号）给远端接口做实体抽取
    """
    if request.method != "POST":
        return HttpResponseBadRequest("只支持 POST")

    try:
        body    = json.loads(request.body.decode("utf-8"))
        text    = body["text"]
        user_id = int(body["user_id"])
        overview = body.get("overview", "")
    except Exception:
        return HttpResponseBadRequest("请求体需包含 text (string) 与 user_id (int)")

    # 1) 按行拆分，并把行号打包
    sentences_with_lines = split_sentences(text)
    sentence_list = [
        {"sentence": item["text"], "line_number": item["line_number"]}
        for item in sentences_with_lines
    ]

    try:
        # 使用新的批量接口进行请求
        headers = {
            "Content-Type": "application/json"
        }

        json_data = {
                "user_id": user_id,
                "research_overview": overview,
                "sentences": sentence_list
            }
        print("json data:", json_data)
        resp = requests.post(
            f"{API_BASE}/extract_entity_batch/",
            # json={
            #     "user_id": user_id,
            #     "research_overview": overview,
            #     "sentences": sentence_list
            # },
            json=json_data,
            headers=headers,
            timeout=1000
        )

        if resp.status_code != 200:
            return HttpResponseBadRequest(f"请求失败: {resp.status_code}")

        # 处理返回结果
        payload = resp.json()
        results = payload.get("results", [])

    except ValueError:
        return HttpResponseBadRequest("无效的 JSON 响应")
    except Exception as e:
        return HttpResponseServerError(f"服务器错误: {str(e)}")

    # 返回最终的实体抽取结果
    return JsonResponse({"sentences": results})


@csrf_exempt
def upload_constructs(request):
    """
    功能: 接收前端提交的 constructs JSON，转发给远端 /constructs/upload/
    {
      "user_id":1,
      "constructs":[ {name, definition, examples}, ... ]
    }
    """
    if request.method != "POST":
        return HttpResponseBadRequest("只支持 POST")
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except:
        return HttpResponseBadRequest("无效 JSON")
    resp = requests.post(
        f"{API_BASE}/constructs/upload/",
        json=payload,
        # timeout=15,
        timeout=1000,
        verify=False
    )
    if resp.status_code == 404:
        # 假设远端 404 时 body 为 {"error":"User not found."}
        return JsonResponse(
            {"error": "User not found."},
            status=404
        )
    payload = resp.json()
    if payload.get("error") == "User not found.":
        return JsonResponse(
            {"error": "User not found."},
            status=404
        )
    return JsonResponse(resp.json(), status=resp.status_code)


@csrf_exempt
def map_constructs(request):
    """
    POST /api/map_constructs/
    接收 JSON:
      {
        "user_id": 1,
        "force": false        # 可选，默认 false
      }
    转发给 <API_BASE>/constructs/map_all_constructs_for_user/ 并原样返回
    """
    if request.method != "POST":
        return HttpResponseBadRequest("只支持 POST")

    try:
        body = json.loads(request.body.decode("utf-8"))
        user_id = int(body["user_id"])
        force = bool(body.get("force", False))
    except (KeyError, ValueError, TypeError):
        return HttpResponseBadRequest("请求体需包含 user_id (int)，可选 force (bool)")

    payload = {"user_id": user_id, "force": force}
    remote_url = f"{API_BASE}/constructs/map_all_constructs_for_user/"

    logger.info(f"[map_constructs] incoming payload → {payload}")
    try:
        resp = requests.post(remote_url, json=payload, timeout=1000)
    except requests.RequestException as err:
        logger.error(f"[map_constructs] upstream request failed: {err}")
        return JsonResponse({"error": f"Upstream failed: {err}"}, status=502)

    logger.info(f"[map_constructs] upstream status={resp.status_code}")
    logger.info(f"[map_constructs] upstream body=\n{resp.text}")

    if resp.status_code != 200:
        return JsonResponse(
            {"error": f"Upstream returned {resp.status_code}", "raw": resp.text},
            status=resp.status_code
        )

    try:
        data = resp.json()
    except ValueError:
        logger.error(f"[map_constructs] non-JSON from upstream: {resp.text}")
        return JsonResponse(
            {"error": "Upstream returned non-JSON", "raw": resp.text},
            status=502
        )

    return JsonResponse(data, status=200)

# @csrf_exempt
# def extract_causals(request):
#     """
#     本地 POST /api/extract_causals/
#     接收 JSON { "user_id": 1 }
#     转发给远端 POST /extract_causals/ 并原样返回它的 JSON
#     """
#     if request.method != "POST":
#         return HttpResponseBadRequest("只支持 POST")
#     try:
#         body    = json.loads(request.body.decode("utf-8"))
#         user_id = int(body["user_id"])
#     except Exception:
#         return HttpResponseBadRequest("请求体需是 JSON 且包含 user_id(int)")
#     remote_url = f"{API_BASE}/extract_causals/"
#     resp = requests.post(
#         remote_url,
#         json={"user_id": user_id},
#         timeout=1000,
#         # timeout=20
#     )
#
#     # try:
#     #     data = resp.json()
#     #     print(f"[extract_causals] 解析后的 JSON:\n{json.dumps(data, ensure_ascii=False, indent=2)}")
#     # except ValueError:
#     #     return JsonResponse(
#     #         {"error": "远端返回非 JSON", "raw": resp.text},
#     #         status=502
#     #     )
#     #
#     # return JsonResponse(data, status=resp.status_code)
#     try:
#         data = resp.json()
#     except Exception as e:
#         return JsonResponse(
#             {"error": f"远端返回异常内容", "detail": str(e), "raw": resp.text[:500]},
#             status=502
#         )
#
#     # 解析成功再返回
#     return JsonResponse(data, status=resp.status_code)


@csrf_exempt
def extract_causals(request):
    if request.method != "POST":
        return HttpResponseBadRequest("只支持 POST")

    try:
        body = json.loads(request.body.decode("utf-8"))
        user_id = int(body["user_id"])
    except Exception:
        return HttpResponseBadRequest("请求体需是 JSON 且包含 user_id(int)")

    remote_url = f"{API_BASE}/extract_causals/"

    try:
        resp = requests.post(
            remote_url,
            json={"user_id": user_id},
            timeout=1000
        )
    except requests.RequestException as e:
        return JsonResponse(
            {"error": f"请求远端失败", "detail": str(e)},
            status=502
        )

    try:
        data = resp.json()
    except Exception as e:
        return JsonResponse(
            {"error": f"远端返回异常内容", "detail": str(e), "raw": resp.text[:500]},
            status=502
        )

    return JsonResponse(data, status=resp.status_code)


@csrf_exempt
def auto_entity_resolution(request):
    """
    POST /api/auto_entity_resolution/
    接收 JSON { "user_id": 1 }
    转发给远端 /auto_entity_resolution/ 并做重试，最后返回 JSON 或错误提示
    """
    if request.method != "POST":
        return HttpResponseBadRequest("只支持 POST")

        # 直接解析 user_id
    body = json.loads(request.body.decode("utf-8"))
    user_id = body["user_id"]

    # 构造 payload 并转发
    payload = {
        "user_id": user_id,
        "k": 5,
        "max_workers": 20
    }
    resp = requests.post(
        f"{API_BASE}/auto_entity_resolution/",
        json=payload,
        timeout=1000
    )

    # 原样透传远端返回
    return JsonResponse(resp.json(), status=resp.status_code)

@csrf_exempt
def create_user_view(request):
    # 1. 解析前端 JSON
    try:
        data = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return HttpResponseBadRequest("Invalid JSON")

    username = (data.get("username") or "").strip()
    email    = (data.get("email")    or "").strip()
    if not username or not email:
        return JsonResponse(
            {"error": "username and email are required"},
            status=400
        )

    # 2. 调用远端创建用户接口
    try:
        resp = requests.post(
            f"{API_BASE}/user/create/",
            json={"username": username, "email": email},
            timeout=1000
        )
    except requests.RequestException as e:
        return JsonResponse(
            {"error": f"Failed to reach remote service: {e}"},
            status=502
        )

    # 3. 如果远端报错就透传它的 JSON 或状态
    if resp.status_code not in (200, 201):
        try:
            return JsonResponse(resp.json(), status=resp.status_code)
        except ValueError:
            return JsonResponse(
                {"error": f"Remote returned status {resp.status_code}"},
                status=resp.status_code
            )

    # 4. 成功：把远端返回的 {message, user_id} 原样返回
    return JsonResponse(resp.json(), status=resp.status_code)