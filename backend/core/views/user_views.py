from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from core.services import user_service

@api_view(['GET'])
def validate_user_view(request, user_id):
    return Response({'valid': user_service.user_exists(user_id)})