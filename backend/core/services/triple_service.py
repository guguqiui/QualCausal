from core.models import Triple, SystemUser, Sentence, Entity
from django.core.exceptions import ObjectDoesNotExist

def get_all_triples(user_id):
    """获取指定用户的所有 triples"""
    return Triple.objects.filter(user__id=user_id)

def get_triple_by_id(triple_id):
    """获取单个 triple"""
    return Triple.objects.get(id=triple_id)

def create_triple(data, user_id):
    """
    data 示例：
    {
        'sentence_id': 1,
        'entity_cause_id': 2,
        'entity_effect_id': 3
    }
    """
    user = SystemUser.objects.get(id=user_id)
    sentence = Sentence.objects.get(id=data['sentence_id'])
    entity_cause = Entity.objects.get(id=data['entity_cause_id'])
    entity_effect = Entity.objects.get(id=data['entity_effect_id'])

    triple = Triple.objects.create(
        user=user,
        sentence=sentence,
        entity_cause=entity_cause,
        entity_effect=entity_effect
    )
    return triple

def update_triple(triple_id, data):
    """
    data 可包含: sentence_id, entity_cause_id, entity_effect_id
    """
    triple = Triple.objects.get(id=triple_id)

    if 'sentence_id' in data:
        triple.sentence = Sentence.objects.get(id=data['sentence_id'])
    if 'entity_cause_id' in data:
        triple.entity_cause = Entity.objects.get(id=data['entity_cause_id'])
    if 'entity_effect_id' in data:
        triple.entity_effect = Entity.objects.get(id=data['entity_effect_id'])

    triple.save()
    return triple

def delete_triple(triple_id):
    triple = Triple.objects.get(id=triple_id)
    triple.delete()