from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from core.services import operation_service
from core.serializers import OperationSerializer
from datetime import datetime

@api_view(['GET'])
def get_user_operations_view(request, user_id):
    ops = operation_service.get_operations_for_user(user_id)
    return Response(OperationSerializer(ops, many=True).data)

@api_view(['POST'])
def add_operations_batch_view(request):
    data = request.data
    if not isinstance(data, list) or len(data) == 0:
        return Response({'error': 'No operations provided'}, status=status.HTTP_400_BAD_REQUEST)

    now = datetime.now()
    for op in data:
        op.setdefault('timestamp', now)

    try:
        operation_service.save_operations_batch(data)
        return Response({'message': 'Operations saved successfully'}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)