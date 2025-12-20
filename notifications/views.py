from rest_framework import status, permissions, viewsets
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.response import Response
from .models import FCMDevice
from django.contrib.auth import get_user_model
from .serializers import FCMDeviceSerializer

User = get_user_model()


def _normalize_token(token: str | None) -> str:
    return (token or '').strip()


def _upsert_fcm_device(*, user, token: str) -> FCMDevice:
    """Create/update an FCMDevice for a token.

    Note: token is unique. If a token already exists for a different user
    (e.g., reinstall/login on another account), re-assign it.
    """
    existing = FCMDevice.objects.filter(token=token).first()
    if existing:
        if existing.user_id != user.id:
            existing.user = user
            existing.save(update_fields=['user', 'updated_at'])
        return existing
    return FCMDevice.objects.create(user=user, token=token)

class SaveFCMTokenRequestSerializer(serializers.Serializer):
    token = serializers.CharField()
    # Legacy: older clients used to send user_id; we ignore it unless it mismatches.
    user_id = serializers.IntegerField(required=False)
    # When true, remove other tokens for this user and keep only the current token.
    replace_other_tokens = serializers.BooleanField(required=False, default=True)

class SaveFCMTokenResponseSerializer(serializers.Serializer):
    status = serializers.CharField()

class SaveFCMTokenView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request=SaveFCMTokenRequestSerializer,
        responses={201: SaveFCMTokenResponseSerializer, 400: SaveFCMTokenResponseSerializer},
    )
    def post(self, request):
        token = _normalize_token(request.data.get('token'))
        if not token:
            return Response({"status": "Missing token"}, status=status.HTTP_400_BAD_REQUEST)

        user_id = request.data.get('user_id')
        if user_id is not None and str(user_id) != str(request.user.id):
            return Response({"status": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

        device = _upsert_fcm_device(user=request.user, token=token)

        replace_other_tokens = request.data.get('replace_other_tokens', True)
        if isinstance(replace_other_tokens, str):
            replace_other_tokens = replace_other_tokens.strip().lower() in {'1', 'true', 't', 'yes', 'y', 'on'}

        if replace_other_tokens:
            FCMDevice.objects.filter(user=request.user).exclude(id=device.id).delete()

        return Response({"status": "Token saved"}, status=status.HTTP_201_CREATED)


class FCMDeviceViewSet(viewsets.ModelViewSet):
    """
    Manage FCM device tokens for the authenticated user. POST is idempotent per-token.
    """
    serializer_class = FCMDeviceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return FCMDevice.objects.none()
        return FCMDevice.objects.filter(user=self.request.user).order_by('-created_at')

    def create(self, request, *args, **kwargs):
        token = _normalize_token(request.data.get('token'))
        if not token:
            return Response({'detail': 'token is required'}, status=status.HTTP_400_BAD_REQUEST)

        replace_other_tokens = request.data.get('replace_other_tokens', False)
        if isinstance(replace_other_tokens, str):
            replace_other_tokens = replace_other_tokens.strip().lower() in {'1', 'true', 't', 'yes', 'y', 'on'}

        obj = _upsert_fcm_device(user=request.user, token=token)
        if replace_other_tokens:
            FCMDevice.objects.filter(user=request.user).exclude(id=obj.id).delete()

        serializer = self.get_serializer(obj)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
