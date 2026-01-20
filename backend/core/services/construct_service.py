from core.models import Construct, SystemUser

def get_all_constructs(user_id):
    return Construct.objects.filter(user__id=user_id)

def get_construct_by_id(construct_id):
    return Construct.objects.get(id=construct_id)

def create_construct(data, user_id):
    user = SystemUser.objects.get(id=user_id)
    return Construct.objects.create(
        user=user,
        name=data['name'],
        definition=data.get('definition', ''),
        examples=data.get('examples', []),
        color=data.get('color', '#cccccc')
    )

def update_construct(construct_id, data):
    construct = Construct.objects.get(id=construct_id)
    construct.name = data.get('name', construct.name)
    construct.definition = data.get('definition', construct.definition)
    construct.examples = data.get('examples', construct.examples)
    construct.color = data.get('color', construct.color)
    construct.save()
    return construct

def delete_construct(construct_id):
    Construct.objects.get(id=construct_id).delete()
