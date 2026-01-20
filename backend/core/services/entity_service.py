from core.models import Entity, Construct, Sentence, SystemUser
from django.core.exceptions import ObjectDoesNotExist

def get_all_entities(user_id):
    return Entity.objects.filter(user__id=user_id)

def get_entity_by_id(entity_id):
    return Entity.objects.get(id=entity_id)

def create_entity(data, user_id):
    user = SystemUser.objects.get(id=user_id)
    construct = Construct.objects.get(id=data.get('construct_id')) if data.get('construct_id') else None
    sentence = Sentence.objects.get(id=data.get('sentence_id')) if data.get('sentence_id') else None
    canonical_entity = Entity.objects.get(id=data.get('canonical_entity_id')) if data.get('canonical_entity_id') else None

    entity = Entity.objects.create(
        user=user,
        name=data['name'],
        construct=construct,
        sentence=sentence,
        embeddings=data.get('embeddings', {}),
        canonical_entity=canonical_entity
    )
    return entity

def update_entity(entity_id, data):
    entity = Entity.objects.get(id=entity_id)
    if 'name' in data:
        entity.name = data['name']
    if 'construct_id' in data:
        entity.construct = Construct.objects.get(id=data['construct_id']) if data['construct_id'] else None
    if 'sentence_id' in data:
        entity.sentence = Sentence.objects.get(id=data['sentence_id']) if data['sentence_id'] else None
    if 'canonical_entity_id' in data:
            entity.canonical_entity_id = data['canonical_entity_id']
    entity.save()
    return entity

def delete_entity(entity_id):
    entity = Entity.objects.get(id=entity_id)
    entity.delete()