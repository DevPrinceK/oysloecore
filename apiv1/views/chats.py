import random
import string

from django.db import IntegrityError
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiParameter

from apiv1.serializers import ChatroomIdResponseSerializer
from accounts.models import User
from apiv1.models import ChatRoom, Product


class GetChatroomIdAPI(APIView):
    '''API to get or create a chatroom between two users'''
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter(name='email', type=str, location=OpenApiParameter.QUERY, required=True),
            OpenApiParameter(
                name='product_id',
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description='Product identifier (numeric id or pid_...) to associate an ad with this chatroom.',
            ),
        ],
        responses={200: ChatroomIdResponseSerializer, 404: ChatroomIdResponseSerializer},
        operation_id='get_chatroom_id'
    )
    def get(self, request, *args, **kwargs):
        """Get or create a private chatroom between the current user and another user.

        The other user is identified by the ``email`` query parameter.
        """
        current_user = request.user
        other_user_email = request.query_params.get('email')
        product_identifier = request.query_params.get('product_id')

        if not other_user_email:
            return Response(
                {"error": "email is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            other_user = User.objects.get(email=other_user_email)
        except User.DoesNotExist:
            return Response(
                {
                    "error": "User not found",
                    "message": "Cannot find user with the provided email.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # Prevent self-chatrooms
        if other_user.id == current_user.id:
            return Response(
                {"error": "Cannot create a chatroom with yourself."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        product = None
        if product_identifier:
            # Support both integer PK and pid string.
            try:
                if str(product_identifier).isdigit():
                    product = Product.objects.filter(id=int(product_identifier)).first()
                else:
                    product = Product.objects.filter(pid=str(product_identifier)).first()
            except Exception:
                product = None

            if not product:
                return Response(
                    {"error": "Product not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

        # Try to find an existing private chatroom containing both users (and matching product if provided)
        qs = (
            ChatRoom.objects
            .filter(is_group=False, members=current_user)
            .filter(members=other_user)
        )
        if product:
            qs = qs.filter(product=product)
        chatroom = qs.first()
        if chatroom:
            return Response(
                {
                    "chatroom_id": chatroom.room_id,
                    "product_id": getattr(chatroom.product, 'pid', '') if getattr(chatroom, 'product', None) else '',
                    "ad_name": getattr(chatroom, 'ad_name', '') or '',
                    "ad_image": getattr(chatroom, 'ad_image_url', '') or '',
                },
                status=status.HTTP_200_OK,
            )

        # Create a new private chatroom with a compact unique name, mirroring the consumer logic
        min_id = min(current_user.id, other_user.id)
        max_id = max(current_user.id, other_user.id)
        base = f"private_{min_id}_{max_id}_"

        for length in (6, 8):
            rand = "".join(random.choices(string.ascii_lowercase + string.digits, k=length))
            name = f"{base}{rand}"
            try:
                chatroom = ChatRoom.objects.create(room_id=name, name=name, is_group=False, product=product)
                chatroom.members.add(current_user, other_user)
                return Response(
                    {
                        "chatroom_id": chatroom.room_id,
                        "product_id": getattr(chatroom.product, 'pid', '') if getattr(chatroom, 'product', None) else '',
                        "ad_name": getattr(chatroom, 'ad_name', '') or '',
                        "ad_image": getattr(chatroom, 'ad_image_url', '') or '',
                    },
                    status=status.HTTP_200_OK,
                )
            except IntegrityError:
                # Try again with a different suffix length
                continue

        # Fallback if creation keeps failing
        return Response(
            {"error": "Unable to create chatroom at this time."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )