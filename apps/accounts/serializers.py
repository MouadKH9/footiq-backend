from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class DeviceRegisterSerializer(serializers.Serializer):
    device_id = serializers.UUIDField()
    platform = serializers.CharField(max_length=20, required=False, default="")


class UpgradeSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8, write_only=True)

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("This email is already in use.")
        return value


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    device_id = serializers.UUIDField()
    platform = serializers.CharField(max_length=20, required=False, default="")
