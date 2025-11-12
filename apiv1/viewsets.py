from requests import request
from rest_framework import permissions, viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response

from apiv1.models import (
    Category, SubCategory, Product, ProductImage,
    Feature, ProductFeature, Review, ChatRoom, Message, Coupon, CouponRedemption
)
from accounts.models import Location
from apiv1.serializers import (
    CategorySerializer, SubCategorySerializer, ProductSerializer, ProductImageSerializer,
    FeatureSerializer, ProductFeatureSerializer, ReviewSerializer,
    ChatRoomSerializer, MessageSerializer, AdminChangeProductStatusSerializer, LocationSerializer, CreateReviewSerializer, AlertSerializer, MarkAsTakenSerializer
)
from django.db import transaction
from django.utils import timezone
from drf_spectacular.utils import extend_schema, OpenApiExample
from oysloecore.sysutils.constants import ProductStatus
from notifications.models import Alert


class IsAuthenticated(permissions.IsAuthenticated):
    pass

class AllowAny(permissions.AllowAny):
    pass

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all().order_by('name')
    serializer_class = CategorySerializer
    permission_classes = [AllowAny, IsAuthenticated]


class SubCategoryViewSet(viewsets.ModelViewSet):
    queryset = SubCategory.objects.all().order_by('name')
    serializer_class = SubCategorySerializer
    permission_classes = [AllowAny, IsAuthenticated]
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
    
    @action(detail=True, methods=['post'], url_path='mark-as-taken')
    @extend_schema(
        request=MarkAsTakenSerializer,
        responses={200: ProductSerializer, 400: None},
        operation_id='product_mark_as_taken',
        description='Mark a product as taken. Only the product owner can perform this action. Body must include the product id.'
    )
    def mark_as_taken(self, request, pk=None):
        product = self.get_object()
        serializer = MarkAsTakenSerializer(data=request.data)
        if not serializer.is_valid():
            first_field, errors = next(iter(serializer.errors.items()))
            return Response({'detail': f'{first_field}: {errors[0]}'}, status=status.HTTP_400_BAD_REQUEST)
        body_product_id = serializer.validated_data['product']
        if int(body_product_id) != int(product.id):
            return Response({'detail': 'product id does not match URL resource id'}, status=status.HTTP_400_BAD_REQUEST)
        # ownership check
        owner = getattr(product, 'owner', None)
        if owner is None:
            return Response({'detail': 'Product has no owner assigned'}, status=status.HTTP_400_BAD_REQUEST)
        if request.user != owner and not request.user.is_staff:
            return Response({'detail': 'You are not allowed to mark this product as taken'}, status=status.HTTP_403_FORBIDDEN)
        if product.is_taken:
            return Response({'detail': 'Product already marked as taken'}, status=status.HTTP_200_OK)
        product.is_taken = True
        product.save(update_fields=['is_taken', 'updated_at'])
        # optional alert to owner
        try:
            Alert.objects.create(
                user=owner,
                title='Product marked as taken',
                body=f'Your product "{product.name}" has been marked as taken.',
                kind='PRODUCT_TAKEN'
            )
        except Exception:
            pass
        return Response(ProductSerializer(product, context={'request': request}).data)


    @action(detail=True, methods=['put'], url_path='set-status', permission_classes=[permissions.IsAdminUser])
    @extend_schema(
        request=AdminChangeProductStatusSerializer,
        responses={200: ProductSerializer, 400: None},
        operation_id='product_set_status',
        description='Update product status (partial: id and status). Staff-only.',
        examples=[
            OpenApiExample(
                'Set product status example',
                value={"id": 42, "status": "ACTIVE"},
                request_only=True,
            )
        ]
    )
    def set_status(self, request, pk=None):
        """Set the product (ad) status. Staff-only."""
        product = self.get_object()
        serializer = AdminChangeProductStatusSerializer(data=request.data)
        if not serializer.is_valid():
            # return first error in consistent shape
            first_field, errors = next(iter(serializer.errors.items()))
            first_error = errors[0]
            return Response({'detail': f'{first_field}: {first_error}'}, status=status.HTTP_400_BAD_REQUEST)
        body_id = serializer.validated_data['id']
        new_status = serializer.validated_data['status']
        # Ensure provided id matches path id
        try:
            if int(body_id) != int(product.id):
                return Response({'detail': 'id in body does not match resource id'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            return Response({'detail': 'Invalid id'}, status=status.HTTP_400_BAD_REQUEST)
        # Optional: guard against unknown even though serializer validates
        if new_status not in [tag.value for tag in ProductStatus]:
            return Response({'detail': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)
        product.status = new_status
        product.save(update_fields=['status', 'updated_at'])
        # generate product approval alert if possible
        if new_status in [ProductStatus.VERIFIED.value, ProductStatus.ACTIVE.value]:
            owner = None
            # Try common owner attribute names
            for attr in ['owner', 'user', 'vendor', 'seller', 'created_by']:
                if hasattr(product, attr):
                    owner = getattr(product, attr)
                    break
            if owner and getattr(owner, 'pk', None):
                try:
                    Alert.objects.create(
                        user=owner,
                        title='Product approved',
                        body=f'Your product "{product.name}" has been approved.',
                        kind='PRODUCT_APPROVED'
                    )
                except Exception:
                    pass
        return Response(ProductSerializer(product, context={'request': request}).data)


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
    permission_classes = [AllowAny, IsAuthenticated]
    filterset_fields = ['product', 'user']
    
    def get_serializer_class(self):
        # Use a write-oriented serializer for creates to accept FK ids directly
        if getattr(self, 'action', None) == 'create':
            return CreateReviewSerializer
        return super().get_serializer_class()

    @extend_schema(request=CreateReviewSerializer, responses={201: ReviewSerializer})
    def create(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response({'detail': 'Authentication credentials were not provided.'}, status=status.HTTP_401_UNAUTHORIZED)
        return super().create(request, *args, **kwargs)
    
    def perform_create(self, serializer):
        if not self.request.user.is_authenticated:
            return Response({'detail': 'Authentication credentials were not provided.'}, status=status.HTTP_401_UNAUTHORIZED)
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


class LocationViewSet(viewsets.ModelViewSet):
    queryset = Location.objects.all().order_by('name')
    serializer_class = LocationSerializer
    permission_classes = [permissions.IsAdminUser, permissions.IsAuthenticated]
    filterset_fields = ['region', 'name']
    search_fields = ['name', 'region']
    ordering_fields = ['name', 'created_at']


class AlertViewSet(viewsets.ReadOnlyModelViewSet):
    """Users can list and retrieve their in-app alerts."""
    serializer_class = AlertSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Alert.objects.filter(user=self.request.user).order_by('-created_at')

    @action(detail=False, methods=['post'], url_path='mark-all-read')
    def mark_all_read(self, request):
        Alert.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({'status': 'ok'})

    @action(detail=True, methods=['post'], url_path='mark-read')
    def mark_read(self, request, pk=None):
        alert = self.get_object()
        if not alert.is_read:
            alert.is_read = True
            alert.save(update_fields=['is_read', 'updated_at'])
        return Response({'status': 'ok'})

    @action(detail=True, methods=['delete'], url_path='delete')
    def delete_alert(self, request, pk=None):
        alert = self.get_object()
        alert.delete()
        return Response({'status': 'deleted'})
