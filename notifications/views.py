from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import FCMDevice
from django.contrib.auth import get_user_model

User = get_user_model()

class SaveFCMTokenView(APIView):
    def post(self, request):
        token = request.data.get("token")
        user_id = request.data.get("user_id")

        if not token or not user_id:
            return Response({"error": "Missing token or user_id"}, status=400)

        user = User.objects.get(id=user_id)
        FCMDevice.objects.update_or_create(user=user, token=token)

        return Response({"status": "Token saved"}, status=201)
