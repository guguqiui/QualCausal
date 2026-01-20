from rest_framework import serializers
from .models import SystemUser, Operation

class OperationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Operation
        fields = '__all__'