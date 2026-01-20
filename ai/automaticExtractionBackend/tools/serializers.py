"""
 @file: serializers.py
 @Time    : 2025/4/14
 @Author  : Peinuan qin
 """
from rest_framework import serializers

from automaticExtractionBackend.models import Construct, Triple
# serializers.py
from rest_framework import serializers
from automaticExtractionBackend.models import Entity, Construct, Sentence, SystemUser

class SystemUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemUser
        fields = ['id', 'username', 'email']


class ConstructSerializer(serializers.ModelSerializer):
    user = SystemUserSerializer(read_only=True)

    class Meta:
        model = Construct
        fields = ['id', 'name', 'definition', 'examples', 'user']


class SentenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sentence
        fields = ['id', 'text']


class EntitySerializer(serializers.ModelSerializer):
    construct = ConstructSerializer(read_only=True)
    sentence = SentenceSerializer(read_only=True)
    canonical_entity = serializers.PrimaryKeyRelatedField(read_only=True)
    user = SystemUserSerializer(read_only=True)

    class Meta:
        model = Entity
        fields = [
            'id',
            'name',
            'construct',
            'sentence',
            'canonical_entity',
            'user',
        ]


class TripleSerializer(serializers.ModelSerializer):
    entity_cause = EntitySerializer(source="entity_cause.canonical_entity", read_only=True)
    entity_effect = EntitySerializer(source="entity_effect.canonical_entity", read_only=True)
    sentence_text = serializers.CharField(source="sentence.text", read_only=True)

    class Meta:
        model = Triple
        fields = ['id', 'entity_cause', 'entity_effect', 'sentence_text']
