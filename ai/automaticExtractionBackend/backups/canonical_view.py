"""
 @file: canonical_view.py
 @Time    : 2025/4/10
 @Author  : Peinuan qin
 """
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods
from django.shortcuts import get_object_or_404

from automaticExtractionBackend.models import Entity, SystemUser, Triple
from django.db import models

from automaticExtractionBackend.tools.serializers import EntitySerializer, TripleSerializer


@csrf_exempt
@require_GET
def get_canonical_group(request, entity_id):
    try:
        canonical = get_object_or_404(Entity, id=entity_id)

        # 如果这个 entity 本身是别名，跳转到真正的 canonical
        if canonical.canonical_entity:
            canonical = canonical.canonical_entity

        # 获取所有指向该 canonical 的 alias，包括它自己
        aliases = Entity.objects.filter(
            models.Q(canonical_entity=canonical) | models.Q(id=canonical.id)
        ).select_related("construct", "sentence")

        alias_list = []
        for e in aliases:
            alias_list.append({
                "id": e.id,
                "name": e.name,
                "construct": e.construct.name if e.construct else None,
                "sentence": e.sentence.text[:80] if e.sentence else None,
                "is_canonical": (e.id == canonical.id),
            })

        return JsonResponse({
            "canonical_id": canonical.id,
            "canonical_name": canonical.name,
            "construct": canonical.construct.name if canonical.construct else None,
            "aliases": alias_list
        }, status=200)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)



@csrf_exempt
@require_http_methods(["GET"])
def entity_cluster_graph(request, user_id):
    """
    """

    try:
        user = SystemUser.objects.get(pk=user_id)
        entities = Entity.objects.filter(user=user).select_related("construct", "canonical_entity")

        # instances 是所有实体（包含其 canonical 指向）
        serialized_instances = EntitySerializer(entities, many=True).data

        canonical_entities = {}

        for e in entities:
            canonical = e.canonical_entity or e
            if canonical.id not in canonical_entities:
                # 确保了只有那些 node 级别的 entity 才会加入进来
                canonical_entities[canonical.id] = canonical

        serialized_nodes = EntitySerializer(canonical_entities.values(), many=True).data

        # 构建实体归属 canonical 的边（不要包含自指）
        links = []

        # 如果前端每个 node 不想有一个初始化的 instance 就加上下面，
        # 反之如果前端每个 node 想有一个初始化的 instance 就注释掉 if
        for inst in serialized_instances:
            if inst["canonical_entity"] and inst["canonical_entity"] != inst["id"]:
                links.append({
                    "source": inst["id"],
                    "target": inst["canonical_entity"]
                })

        triples = Triple.objects.filter(user=user).select_related("entity_cause__canonical_entity",
                                                                  "entity_effect__canonical_entity", "sentence")
        serialized_triples = TripleSerializer(triples, many=True).data

        return JsonResponse({
            "instances": serialized_instances,
            "nodes": serialized_nodes,
            "links": links,
            "triples": serialized_triples
        }, status=200)

    except SystemUser.DoesNotExist:
        return JsonResponse({"error": "User not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
