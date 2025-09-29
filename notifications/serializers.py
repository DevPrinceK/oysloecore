from rest_framework import serializers
from .models import FCMDevice


class FCMDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = FCMDevice
        fields = ['id', 'user', 'token', 'created_at']
        read_only_fields = ['id', 'created_at', 'user']
