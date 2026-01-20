from core.models import Operation

def get_operations_for_user(user_id):
    return Operation.objects.filter(user_id=user_id).order_by('timestamp')

def save_operations_batch(ops_data):
    ops = [Operation(**data) for data in ops_data]
    Operation.objects.bulk_create(ops)