import json
import requests
from core.utils.http import session
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from core.models import SystemUser, Construct, Sentence, Entity, Triple
from visualizationBackendProject.settings import API_BASE

# API_BASE = "http://ec2-18-143-66-195.ap-southeast-1.compute.amazonaws.com"
# API_BASE = "http://localhost:8001"

@csrf_exempt
def import_data(request):
    """
    本地 GET/POST /api/import-data/ 接收 user_id，
    如果不存在该 SystemUser，就创建一个，然后把远端数据导入到本地。
    """
    # 1. 解析 user_id
    if request.method == "GET":
        uid = request.GET.get("user_id")
    else:
        try:
            body = json.loads(request.body.decode())
            uid  = body.get("user_id")
        except Exception:
            uid = None

    try:
        user_id = int(uid)
    except Exception:
        return HttpResponseBadRequest("需要提供 user_id（整数）")

    # 2. 如果本地没有这个 user，就新建一个
    user, created = SystemUser.objects.get_or_create(
        id=user_id,
        defaults={
            # 根据你 SystemUser 的字段，填写必要的默认值
            "username": f"user_{user_id}",
            "email":    f"user_{user_id}@example.com",
            # ... 如果还有其它必填字段也要在这里给个 defaults ...
        }
    )
    if created:
        print(f"[import_data] Created new SystemUser with id={user_id}")

    # 3. 调用远端 export 接口
    resp = requests.get(f"{API_BASE}/export/{user_id}/", timeout=30)
    if resp.status_code != 200:
        return JsonResponse(
            {"status":"error", "message":f"Export 接口返回 {resp.status_code}"},
            status=502
        )
    data = resp.json()

    # 4. 在事务中导入清空再写入
    with transaction.atomic():
        Construct.objects.filter(user=user).delete()
        Sentence.objects.filter(user=user).delete()
        Entity.objects.filter(user=user).delete()
        Triple.objects.filter(user=user).delete()

        construct_map = {}
        sentence_map  = {}
        entity_map    = {}
        canonical_map = {}

        # 导入 constructs
        for c in data.get("constructs", []):
            print(c)
            obj = Construct.objects.create(
                user=user,
                name=c["name"],
                definition=c.get("definition",""),
                examples=c.get("examples",[]),
                color=c.get("color", "#cccccc")
            )
            construct_map[c["id"]] = obj

        # 导入 sentences
        for s in data.get("sentences", []):
            obj = Sentence.objects.create(
                user=user,
                text=s["text"],
                line_number=s.get("line_number", 1)
            )
            sentence_map[s["id"]] = obj

        # 导入 entities
        for e in data.get("entities", []):
            obj = Entity.objects.create(
                user=user,
                name=e["name"],
                construct=construct_map.get(e.get("construct")),
                sentence=sentence_map.get(e.get("sentence")),
                embeddings=e.get("embeddings", {})
            )
            entity_map[e["id"]]    = obj
            canonical_map[e["id"]] = e.get("canonical_entity")

        # 第二轮：关联 canonical_entity
        for eid, cid in canonical_map.items():
            if cid and cid in entity_map:
                ent = entity_map[eid]
                ent.canonical_entity = entity_map[cid]
                ent.save()

        # 导入 triples
        for t in data.get("triples", []):
            Triple.objects.create(
                user=user,
                sentence      = sentence_map[t["sentence"]["id"]],
                entity_cause  = entity_map[t["entity_cause"]["id"]],
                entity_effect = entity_map[t["entity_effect"]["id"]]
            )

    return JsonResponse({"status":"success","message":"已成功导入本地数据库"})