from core.models import SystemUser
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings

TEMPLATE_USER_ID = getattr(settings, 'TEMPLATE_USER_ID', 'template')

def user_exists(user_id):
    return SystemUser.objects.filter(pk=user_id).exists()
