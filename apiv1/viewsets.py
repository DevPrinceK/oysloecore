from rest_framework import permissions, viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response

from apiv1.models import (
    Category, SubCategory, Product, ProductImage,
    Feature, ProductFeature, Review, ChatRoom, Message, Coupon, CouponRedemption
)
from apiv1.serializers import (
    CategorySerializer, SubCategorySerializer, ProductSerializer, ProductImageSerializer,
    FeatureSerializer, ProductFeatureSerializer, ReviewSerializer,
    ChatRoomSerializer, MessageSerializer
)
from django.db import transaction
from django.utils import timezone


class IsAuthenticated(permissions.IsAuthenticated):
    pass

class AllowAny(permissions.AllowAny):
    pass

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all().order_by('name')
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]


class SubCategoryViewSet(viewsets.ModelViewSet):
    queryset = SubCategory.objects.all().order_by('name')
    serializer_class = SubCategorySerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['category']


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all().order_by('-created_at')
    serializer_class = ProductSerializer
    # permission_classes = [IsAuthenticated]
    permission_classes = [AllowAny]
    filterset_fields = ['category', 'pid']
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'price']
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]

    @action(detail=False, methods=['get'], url_path='related')
    def related(self, request):
        category_id = request.query_params.get('category_id')
        qs = Product.objects.filter(category__id=category_id).order_by('?')[:50] if category_id else Product.objects.none()
        return Response(self.get_serializer(qs, many=True).data)


class ProductImageViewSet(viewsets.ModelViewSet):
    queryset = ProductImage.objects.all().order_by('-created_at')
    serializer_class = ProductImageSerializer
    permission_classes = [AllowAny]
    filterset_fields = ['product']


class FeatureViewSet(viewsets.ModelViewSet):
    queryset = Feature.objects.all().order_by('name')
    serializer_class = FeatureSerializer
    permission_classes = [AllowAny]
    filterset_fields = ['subcategory']


class ProductFeatureViewSet(viewsets.ModelViewSet):
    queryset = ProductFeature.objects.all()
    serializer_class = ProductFeatureSerializer
    permission_classes = [AllowAny]
    filterset_fields = ['product', 'feature']


class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.all().order_by('-created_at')
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['product', 'user']

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class MessageViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['room']

    def get_queryset(self):
        # During schema generation, spectacular sets swagger_fake_view to True
        if getattr(self, 'swagger_fake_view', False):  # pragma: no cover
            return Message.objects.none()
        user = self.request.user
        return Message.objects.filter(room__members=user).order_by('-created_at')


class ChatRoomViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ChatRoomSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):  # pragma: no cover
            return ChatRoom.objects.none()
        return ChatRoom.objects.filter(members=self.request.user).order_by('-created_at')

    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        room = self.get_object()
        msgs = room.messages.order_by('created_at')
        return Response(MessageSerializer(msgs, many=True).data)

    @action(detail=True, methods=['post'])
    def send(self, request, pk=None):
        room = self.get_object()
        content = request.data.get('message') or request.data.get('content')
        if not content:
            return Response({'detail': 'message is required'}, status=status.HTTP_400_BAD_REQUEST)
        msg = Message.objects.create(room=room, sender=request.user, content=content)
        return Response(MessageSerializer(msg).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='mark-read')
    def mark_read(self, request, pk=None):
        room = self.get_object()
        room.read_all_messages(request.user)
        return Response({'status': 'ok'})


class CouponViewSet(viewsets.ModelViewSet):
    queryset = Coupon.objects.all().order_by('-created_at')
    serializer_class = apiv1.serializers.CouponSerializer if False else None  # placeholder for import cycle prevention
    permission_classes = [IsAuthenticated]
    filterset_fields = ['code', 'is_active', 'discount_type']
    search_fields = ['code', 'description']
    ordering_fields = ['created_at', 'updated_at']

    def get_serializer_class(self):
        from apiv1.serializers import CouponSerializer  # local import to avoid circular
        return CouponSerializer

    @action(detail=True, methods=['post'])
    def expire(self, request, pk=None):
        coupon = self.get_object()
        coupon.is_active = False
        coupon.valid_until = coupon.valid_until or timezone.now()
        coupon.save(update_fields=['is_active', 'valid_until', 'updated_at'])
        return Response({'status': 'expired'})

    @action(detail=True, methods=['post'])
    def redeem(self, request, pk=None):
        coupon = self.get_object()
        user = request.user
        if not coupon.is_active:
            return Response({'detail': 'Coupon is not active'}, status=status.HTTP_400_BAD_REQUEST)
        if not coupon.is_within_validity():
            return Response({'detail': 'Coupon is not within validity period'}, status=status.HTTP_400_BAD_REQUEST)

        # check global uses
        if coupon.max_uses is not None and coupon.uses >= coupon.max_uses:
            return Response({'detail': 'Coupon usage limit reached'}, status=status.HTTP_400_BAD_REQUEST)

        # check per-user limit
        if coupon.per_user_limit is not None:
            user_uses = CouponRedemption.objects.filter(coupon=coupon, user=user).count()
            if user_uses >= coupon.per_user_limit:
                return Response({'detail': 'Per-user usage limit reached'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            # increment uses and record redemption
            coupon.uses = models.F('uses') + 1  # type: ignore
            coupon.save(update_fields=['uses', 'updated_at'])
            CouponRedemption.objects.create(coupon=coupon, user=user)

        coupon.refresh_from_db()
        from apiv1.serializers import CouponSerializer
        return Response({'coupon': CouponSerializer(coupon).data, 'status': 'redeemed'})
