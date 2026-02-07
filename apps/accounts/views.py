import uuid

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import DeviceSession
from apps.accounts.serializers import (
    DeviceRegisterSerializer,
    LoginSerializer,
    UpgradeSerializer,
)
from apps.accounts.services import merge_anonymous_into_email_user

User = get_user_model()


def _get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
    }


class DeviceRegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = DeviceRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        device_id = serializer.validated_data["device_id"]
        platform = serializer.validated_data.get("platform", "")

        # Check if device already exists
        try:
            device = DeviceSession.objects.select_related("user").get(
                device_id=device_id
            )
            device.save(update_fields=["last_seen_at"])
            tokens = _get_tokens_for_user(device.user)
            return Response(
                {
                    "user_id": str(device.user.id),
                    "is_anonymous": device.user.is_anonymous_user,
                    **tokens,
                }
            )
        except DeviceSession.DoesNotExist:
            pass

        # Create new anonymous user + device
        user = User.objects.create(
            username=f"anon-{uuid.uuid4().hex[:12]}",
            is_anonymous_user=True,
        )
        DeviceSession.objects.create(
            device_id=device_id,
            user=user,
            platform=platform,
        )
        tokens = _get_tokens_for_user(user)
        return Response(
            {
                "user_id": str(user.id),
                "is_anonymous": True,
                **tokens,
            },
            status=status.HTTP_201_CREATED,
        )


class UpgradeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = UpgradeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        if not user.is_anonymous_user:
            return Response(
                {"detail": "Account is already upgraded."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.email = serializer.validated_data["email"]
        user.set_password(serializer.validated_data["password"])
        user.is_anonymous_user = False
        user.save(update_fields=["email", "password", "is_anonymous_user"])

        tokens = _get_tokens_for_user(user)
        return Response(
            {
                "user_id": str(user.id),
                "is_anonymous": False,
                **tokens,
            }
        )


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]
        device_id = serializer.validated_data["device_id"]
        platform = serializer.validated_data.get("platform", "")

        # Authenticate by email
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {"detail": "Invalid email or password."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not user.check_password(password):
            return Response(
                {"detail": "Invalid email or password."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Check if device had an anonymous user
        try:
            device = DeviceSession.objects.select_related("user").get(
                device_id=device_id
            )
            old_user = device.user
            if old_user != user and old_user.is_anonymous_user:
                merge_anonymous_into_email_user(old_user, user)
            # Reassign device to the email user
            device.user = user
            device.platform = platform or device.platform
            device.save(update_fields=["user", "platform", "last_seen_at"])
        except DeviceSession.DoesNotExist:
            DeviceSession.objects.create(
                device_id=device_id,
                user=user,
                platform=platform,
            )

        tokens = _get_tokens_for_user(user)
        return Response(
            {
                "user_id": str(user.id),
                "is_anonymous": False,
                **tokens,
            }
        )
