# """
#  @file: export_view.py
#  @Time    : 2025/4/5
#  @Author  : Peinuan qin
#  """
#
from rest_framework import serializers
from automaticExtractionBackend.models import Construct, Sentence, Entity, Triple, SystemUser
# from rest_framework.decorators import api_view
# from rest_framework.response import Response

# class ConstructSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Construct
#         fields = '__all__'

class ConstructSerializer(serializers.ModelSerializer):
    class Meta:
        model = Construct
        fields = ['id', 'name', 'definition', 'examples']


class SentenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sentence
        fields = '__all__'

class EntitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Entity
        fields = '__all__'

# class TripleSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Triple
#         fields = '__all__'

#
# @api_view(['GET'])
# def export_user_data(request, user_id):
#     try:
#         user = SystemUser.objects.get(pk=user_id)
#     except SystemUser.DoesNotExist:
#         return Response({"error": "User not found."}, status=404)
#
#     constructs = Construct.objects.filter(user=user)
#     sentences = Sentence.objects.filter(user=user)
#     entities = Entity.objects.filter(user=user)
#     triples = Triple.objects.filter(user=user)
#
#     construct_data = ConstructSerializer(constructs, many=True).data
#     sentence_data = SentenceSerializer(sentences, many=True).data
#     entity_data = EntitySerializer(entities, many=True).data
#     triple_data = TripleSerializer(triples, many=True).data
#
#     result = {
#         "user_id": user.id,
#         "username": user.username,
#         "email": user.email,
#         "constructs": construct_data,
#         "sentences": sentence_data,
#         "entities": entity_data,
#         "triples": triple_data
#     }
#
#     return Response(result)


from rest_framework import serializers
from automaticExtractionBackend.models import Triple, Sentence, Entity


class EntitySimpleSerializer(serializers.ModelSerializer):
    construct = ConstructSerializer()
    class Meta:
        model = Entity
        fields = ['id', 'name', 'construct']  # 只显示实体名


class SentenceSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sentence
        fields = ['id', 'text']


class TripleSerializer(serializers.ModelSerializer):
    user = serializers.CharField(source='user.username')  # 转为用户名
    sentence = SentenceSimpleSerializer()
    entity_cause = EntitySimpleSerializer()
    entity_effect = EntitySimpleSerializer()

    class Meta:
        model = Triple
        fields = ['id', 'user', 'sentence', 'entity_cause', 'entity_effect']




import json
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from automaticExtractionBackend.models import SystemUser, Construct, Sentence, Entity, Triple

@require_http_methods(["GET"])
def export_user_data(request, user_id):
    """
    GET /export/1/?fields=constructs,entities
    """
    try:
        user = SystemUser.objects.get(pk=user_id)
    except SystemUser.DoesNotExist:
        return JsonResponse({"error": "User not found."}, status=404)

    # 获取 ?fields=constructs,entities 形式的参数
    fields_param = request.GET.get('fields')
    allowed_fields = {'constructs', 'sentences', 'entities', 'triples'}
    requested_fields = set(fields_param.split(',')) if fields_param else allowed_fields
    requested_fields = requested_fields & allowed_fields  # 防止非法字段

    result = {
        "user_id": user.id,
        "username": user.username,
        "email": user.email,
    }

    # if 'constructs' in requested_fields:
    #     result["constructs"] = list(Construct.objects.filter(user=user).values())
    # if 'sentences' in requested_fields:
    #     result["sentences"] = list(Sentence.objects.filter(user=user).values())
    # if 'entities' in requested_fields:
    #     result["entities"] = list(Entity.objects.filter(user=user).values())
    # if 'triples' in requested_fields:
    #     result["triples"] = list(Triple.objects.filter(user=user).values())

    if 'constructs' in requested_fields:
        constructs = Construct.objects.filter(user=user)
        result["constructs"] = ConstructSerializer(constructs, many=True).data

    if 'sentences' in requested_fields:
        sentences = Sentence.objects.filter(user=user)
        result["sentences"] = SentenceSerializer(sentences, many=True).data

    if 'entities' in requested_fields:
        entities = Entity.objects.filter(user=user)
        result["entities"] = EntitySerializer(entities, many=True).data

    if 'triples' in requested_fields:
        triples = Triple.objects.filter(user=user)
        result["triples"] = TripleSerializer(triples, many=True).data

    return JsonResponse(result, json_dumps_params={'ensure_ascii': False, 'indent': 2})
