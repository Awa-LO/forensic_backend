# authentication/serializers.py

from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import CustomUser

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()
    device_id = serializers.CharField(required=False)

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    device_id = serializers.CharField()

    class Meta:
        model = CustomUser
        fields = ('username', 'password', 'email', 'device_id')

    def create(self, validated_data):
        user = CustomUser.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password'],
            device_id=validated_data['device_id']
        )
        return user