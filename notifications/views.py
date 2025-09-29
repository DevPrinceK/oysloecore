from rest_framework import status, permissions, viewsets
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.response import Response
from .models import FCMDevice
from django.contrib.auth import get_user_model
from .serializers import FCMDeviceSerializer

User = get_user_model()

class SaveFCMTokenRequestSerializer(serializers.Serializer):
    token = serializers.CharField()
    user_id = serializers.IntegerField()

@extend_schema(
    request=SaveFCMTokenRequestSerializer,
    responses={201: {"status": "Token saved"}, 400: {"error": "Missing token or user_id"}},
    operation_id='save_fcm_token'
)
class SaveFCMTokenView(APIView):
    def post(self, request):
        token = request.data.get("token")
        user_id = request.data.get("user_id")

        if not token or not user_id:
            return Response({"error": "Missing token or user_id"}, status=400)

        user = User.objects.get(id=user_id)
        FCMDevice.objects.update_or_create(user=user, token=token)

        return Response({"status": "Token saved"}, status=201)


class FCMDeviceViewSet(viewsets.ModelViewSet):
    """
    Manage FCM device tokens for the authenticated user. POST is idempotent per-token.
    """
    serializer_class = FCMDeviceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return FCMDevice.objects.filter(user=self.request.user).order_by('-created_at')

    def create(self, request, *args, **kwargs):
        token = request.data.get('token')
        if not token:
            return Response({'detail': 'token is required'}, status=status.HTTP_400_BAD_REQUEST)
        obj, _ = FCMDevice.objects.update_or_create(user=request.user, token=token)
        serializer = self.get_serializer(obj)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
