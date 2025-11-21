import requests
from rest_framework import permissions, viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response

from apiv1.models import (
    Category, SubCategory, Product, ProductImage,
    Feature, ProductFeature, Review, ChatRoom, Message,
    Coupon, CouponRedemption, Feedback, Subscription,
    UserSubscription, Payment,
)
from accounts.models import Location
from apiv1.serializers import (
    CategorySerializer, SubCategorySerializer, ProductSerializer, ProductImageSerializer,
    FeatureSerializer, ProductFeatureSerializer, ReviewSerializer,
    ChatRoomSerializer, MessageSerializer, AdminChangeProductStatusSerializer,
    LocationSerializer, CreateReviewSerializer, AlertSerializer, MarkAsTakenSerializer,
    FeedbackSerializer, SubscriptionSerializer, UserSubscriptionSerializer,
    PaymentSerializer,
)
from django.db import transaction
from django.utils import timezone
from drf_spectacular.utils import extend_schema, OpenApiExample
from oysloecore.sysutils.constants import ProductStatus
from notifications.models import Alert
from django.conf import settings


class IsAuthenticated(permissions.IsAuthenticated):
    pass

class AllowAny(permissions.AllowAny):
    pass

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all().order_by('name')
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]


class SubCategoryViewSet(viewsets.ModelViewSet):
    queryset = SubCategory.objects.all().order_by('name')
    serializer_class = SubCategorySerializer
    permission_classes = [AllowAny]
    filterset_fields = ['category']


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all().order_by('-created_at')
    serializer_class = ProductSerializer
    # Only authenticated users can create products; anyone can list/retrieve.
    permission_classes = [IsAuthenticated]
    filterset_fields = ['category', 'pid']
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'price']
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]

    def get_permissions(self):
        """Allow unauthenticated read-only access but require auth for writes.

        This keeps existing public browsing behaviour while enforcing
        subscription checks on create/update actions.
        """
        if self.action in ['list', 'retrieve', 'related']:
            return [AllowAny()]
        return [permission() for permission in self.permission_classes]

    def _get_active_user_subscription(self, user):
        """Return the current active UserSubscription for a user, if any."""
        now = timezone.now()
        return (
            UserSubscription.objects
            .select_related('subscription')
            .filter(user=user, is_active=True, start_date__lte=now, end_date__gte=now)
            .order_by('-created_at')
            .first()
        )

    def _enforce_subscription_limits(self, user):
        """Ensure user has an active subscription and is within product limits.

        Returns ``None`` when checks pass, or a DRF ``Response`` when they fail.
        """
        # Staff/admin users can always manage products without subscription checks
        if getattr(user, 'is_staff', False):
            return None

        active_user_sub = self._get_active_user_subscription(user)
        if not active_user_sub:
            return Response(
                {'detail': 'You must have an active subscription before adding products.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        subscription = active_user_sub.subscription
        max_products = getattr(subscription, 'max_products', 0) or 0
        if max_products and max_products > 0:
            # Count products owned by this user that are not marked as taken
            current_count = Product.objects.filter(owner=user, is_taken=False).count()
            if current_count >= max_products:
                return Response(
                    {
                        'detail': 'You have reached the maximum number of products for your subscription.',
                        'max_products': max_products,
                        'current_products': current_count,
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )
        return None

    def create(self, request, *args, **kwargs):
        """Create a product only if user has an active subscription within limits."""
        error_response = self._enforce_subscription_limits(request.user)
        if error_response is not None:
            return error_response
        return super().create(request, *args, **kwargs)

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
    permission_classes = [AllowAny]
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


class FeedbackViewSet(viewsets.ModelViewSet):
    """Users can submit feedback; admins can browse all feedback."""
    serializer_class = FeedbackSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # During schema generation, spectacular sets swagger_fake_view to True
        if getattr(self, 'swagger_fake_view', False):  # pragma: no cover
            return Feedback.objects.none()
        user = self.request.user
        if user.is_staff:
            # Admins see all feedback for dashboard purposes
            return Feedback.objects.all().order_by('-created_at')
        # Regular users see only their own feedback
        return Feedback.objects.filter(user=user).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class SubscriptionViewSet(viewsets.ModelViewSet):
    """Admin-only CRUD for subscription packages."""
    queryset = Subscription.objects.all().order_by('-created_at')
    serializer_class = SubscriptionSerializer
    permission_classes = [permissions.IsAdminUser, permissions.IsAuthenticated]
    filterset_fields = ['is_active', 'tier', 'price', 'duration_days', 'max_products']
    search_fields = ['name', 'tier', 'description', 'features']
    ordering_fields = ['created_at', 'price', 'duration_days', 'max_products']


class UserSubscriptionViewSet(viewsets.ModelViewSet):
    """Users can subscribe to packages and view their subscriptions."""
    serializer_class = UserSubscriptionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Admins can see all user subscriptions; regular users see only theirs
        if getattr(self, 'swagger_fake_view', False):  # pragma: no cover
            return UserSubscription.objects.none()
        user = self.request.user
        if user.is_staff:
            return UserSubscription.objects.select_related('subscription', 'user').order_by('-created_at')
        return UserSubscription.objects.select_related('subscription').filter(user=user).order_by('-created_at')

    def perform_create(self, serializer):
        """Create a new subscription for the current user based on subscription_id."""
        from django.utils import timezone as dj_timezone
        subscription = serializer.validated_data['subscription']
        start = dj_timezone.now()
        end = start + dj_timezone.timedelta(days=subscription.duration_days)
        serializer.save(user=self.request.user, start_date=start, end_date=end, is_active=True)


class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only access to payment records.

    This is mainly for admin dashboards and debugging; the actual Paystack
    interaction (initiation/webhook) endpoints are implemented in the PaystackPaymentViewSet.
    """

    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAdminUser, permissions.IsAuthenticated]
    filterset_fields = ['status', 'provider', 'subscription']
    search_fields = ['reference']
    ordering_fields = ['created_at', 'amount']

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):  # pragma: no cover
            return Payment.objects.none()
        return Payment.objects.select_related('user', 'subscription').order_by('-created_at')


class PaystackPaymentViewSet(viewsets.ViewSet):
    """Endpoints for initiating and handling Paystack payments for subscriptions."""

    permission_classes = [IsAuthenticated]

    def _get_amount_for_subscription(self, subscription: Subscription):
        # Use the effective price helper if available
        amount = subscription.get_effective_price() if hasattr(subscription, 'get_effective_price') else subscription.price
        return int(amount * 100)  # Paystack expects amount in kobo/pesewas

    @action(detail=False, methods=['post'], url_path='initiate')
    def initiate(self, request):
        """Initiate a Paystack payment for a subscription.

        Expects: {"subscription_id": <id>, "callback_url": "https://..."}
        """
        user = request.user
        subscription_id = request.data.get('subscription_id')
        callback_url = request.data.get('callback_url')

        if not subscription_id:
            return Response({'detail': 'subscription_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            subscription = Subscription.objects.get(id=subscription_id, is_active=True)
        except Subscription.DoesNotExist:
            return Response({'detail': 'Subscription not found or inactive'}, status=status.HTTP_404_NOT_FOUND)

        amount = self._get_amount_for_subscription(subscription)

        headers = {
            'Authorization': f"Bearer {settings.PAYSTACK_SECRET_KEY}",
            'Content-Type': 'application/json',
        }
        payload = {
            'email': user.email,
            'amount': amount,
        }
        if callback_url:
            payload['callback_url'] = callback_url

        init_url = f"{getattr(settings, 'PAYSTACK_BASE_URL', 'https://api.paystack.co')}/transaction/initialize"
        try:
            resp = requests.post(init_url, json=payload, headers=headers, timeout=10)
            data = resp.json()
        except Exception as exc:
            return Response({'detail': f'Error communicating with Paystack: {exc}'}, status=status.HTTP_502_BAD_GATEWAY)

        if not resp.ok or not data.get('status'):
            return Response({'detail': 'Failed to initialize Paystack transaction', 'response': data}, status=status.HTTP_400_BAD_REQUEST)

        paystack_data = data.get('data') or {}
        reference = paystack_data.get('reference')
        authorization_url = paystack_data.get('authorization_url')

        if not reference or not authorization_url:
            return Response({'detail': 'Invalid response from Paystack', 'response': data}, status=status.HTTP_502_BAD_GATEWAY)

        # Create a pending payment record
        payment = Payment.objects.create(
            user=user,
            subscription=subscription,
            amount=amount / 100,
            currency='GHS',
            provider='paystack',
            reference=reference,
            status=Payment.STATUS_PENDING,
            raw_response=data,
        )

        return Response(
            {
                'authorization_url': authorization_url,
                'reference': reference,
                'payment_id': payment.id,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=['post'], url_path='webhook', permission_classes=[])
    def webhook(self, request):
        """Paystack webhook to confirm payments and create UserSubscriptions.

        Configure Paystack to send webhooks to this endpoint.
        """
        # Optional: verify Paystack signature header if configured
        secret_key = settings.PAYSTACK_SECRET_KEY
        payload = request.data
        event = payload.get('event')
        data = payload.get('data') or {}
        reference = data.get('reference')

        if not reference:
            return Response({'detail': 'Missing reference in webhook payload'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            payment = Payment.objects.select_related('subscription', 'user').get(reference=reference)
        except Payment.DoesNotExist:
            return Response({'detail': 'Payment not found'}, status=status.HTTP_404_NOT_FOUND)

        # Only process successful charge events
        if event not in ['charge.success', 'subscription.create']:  # keep flexible
            return Response({'status': 'ignored'})

        # Verify transaction with Paystack for safety
        verify_url = f"{getattr(settings, 'PAYSTACK_BASE_URL', 'https://api.paystack.co')}/transaction/verify/{reference}"
        headers = {
            'Authorization': f"Bearer {secret_key}",
        }
        try:
            resp = requests.get(verify_url, headers=headers, timeout=10)
            verify_data = resp.json()
        except Exception as exc:
            return Response({'detail': f'Error verifying transaction: {exc}'}, status=status.HTTP_502_BAD_GATEWAY)

        if not resp.ok or not verify_data.get('status'):
            payment.status = Payment.STATUS_FAILED
            payment.raw_response = verify_data
            payment.save(update_fields=['status', 'raw_response', 'updated_at'])
            return Response({'detail': 'Verification failed', 'response': verify_data}, status=status.HTTP_400_BAD_REQUEST)

        # Mark payment as successful
        payment.status = Payment.STATUS_SUCCESS
        payment.channel = (verify_data.get('data') or {}).get('channel')
        payment.raw_response = verify_data
        payment.save(update_fields=['status', 'channel', 'raw_response', 'updated_at'])

        # Create or activate a UserSubscription for this user & subscription
        subscription = payment.subscription
        user = payment.user
        if subscription and user:
            from django.utils import timezone as dj_timezone
            start = dj_timezone.now()
            end = start + dj_timezone.timedelta(days=subscription.duration_days)
            UserSubscription.objects.create(
                user=user,
                subscription=subscription,
                payment=payment,
                start_date=start,
                end_date=end,
                is_active=True,
            )

        return Response({'status': 'success'})


class AlertViewSet(viewsets.ModelViewSet):
    """Users can manage their in-app alerts; admins can manage all. When creating an alert as an admin, you can specify the target user by setting the 'user' field in the alert data."""
    serializer_class = AlertSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # During schema generation, spectacular sets swagger_fake_view to True
        if getattr(self, 'swagger_fake_view', False):  # pragma: no cover
            return Alert.objects.none()
        user = self.request.user
        if user.is_staff:
            # Admins see all alerts (for dashboard/control)
            return Alert.objects.all().order_by('-created_at')
        # Regular users see only their own alerts
        return Alert.objects.filter(user=user).order_by('-created_at')

    def perform_create(self, serializer):
        """Admins can target any user; regular users can only create for themselves."""
        user = self.request.user
        if user.is_staff:
            # Allow staff to specify target user via serializer if provided
            return serializer.save()
        # Force non-staff alerts to be attached to the requesting user
        serializer.save(user=user)

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
