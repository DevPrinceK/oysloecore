from django.contrib.auth import authenticate
from rest_framework import serializers

from accounts.models import User
from apiv1.models import (
    ChatRoom,
    Message,
    Product,
    ProductImage,
    Category,
    Review,
    SubCategory,
    Feature,
    PosibleFeatureValue,
    ProductFeature,
    Coupon,
    CouponRedemption,
    Feedback,
    Subscription,
    UserSubscription,
    Payment,
    AccountDeleteRequest,
    PrivacyPolicy,
    TermsAndConditions,
    Favourite,
    ProductLike,
    ProductReport,
    Location,
    JobApplication,
)
from notifications.models import Alert
from oysloecore.sysutils.constants import ProductStatus


class UserSerializer(serializers.ModelSerializer):
    active_ads = serializers.IntegerField(read_only=True)
    taken_ads = serializers.IntegerField(read_only=True)
    total_ads = serializers.IntegerField(read_only=True)
    total_taken_ads = serializers.IntegerField(read_only=True)
    class Meta:
        model = User
        exclude = ["password", "groups", "user_permissions"]


class AdminVerifyIdSerializer(serializers.Serializer):
    """Serializer used by admins to toggle a user's ID verification flag."""
    id = serializers.IntegerField()
    id_verified = serializers.BooleanField()


class CreateUserSerializer(serializers.ModelSerializer):
    """Serializer for creating a user from admin panel"""

    class Meta:
        model = User
        fields = ["email", "phone", "name", "address", "avatar", "password"]
        extra_kwargs = {
            "password": {"write_only": True},
            "email": {"required": True},
            "phone": {"required": True},
        }

    def create(self, validated_data):
        return User.objects.create_user(
            phone=validated_data.get("phone"),
            email=validated_data.get("email"),
            password=validated_data.get("password"),
            name=validated_data.get("name"),
            address=validated_data.get("address"),
            avatar=validated_data.get("avatar"),
        )


class LoginSerializer(serializers.Serializer):
    email = serializers.CharField()
    password = serializers.CharField()

    def validate(self, data):
        user = authenticate(**data)
        if user and user.is_active and ((hasattr(user, "deleted") and user.deleted == False) or not hasattr(user, "deleted")):
            return user
        raise serializers.ValidationError("Incorrect Credentials")


class RegisterUserSerializer(serializers.ModelSerializer):
    referral_code = serializers.CharField(required=False, allow_blank=True)
    class Meta:
        model = User
        fields = ("email", "phone", "password", "name", "address", "referral_code")
        extra_kwargs = {"password": {"write_only": True}, "email": {"required": True}, "phone": {"required": True}}

    def validate(self, attrs):
        if User.objects.filter(email=attrs.get("email")).exists():
            raise serializers.ValidationError("Email already exists")
        if User.objects.filter(phone=attrs.get("phone")).exists():
            raise serializers.ValidationError("Phone already exists")
        return attrs

    def create(self, validated_data):
        from oysloecore.sysutils.services import apply_referral_bonus
        referral_code = validated_data.pop("referral_code", None)
        user = User.objects.create_user(
            phone=validated_data.get("phone"),
            email=validated_data.get("email"),
            password=validated_data.get("password"),
            name=validated_data.get("name"),
            address=validated_data.get("address"),
        )
        # apply referral immediately if provided and valid
        if referral_code:
            inviter = User.objects.filter(referral_code=referral_code).first()
            if inviter and inviter.id != user.id:
                apply_referral_bonus(inviter=inviter, invitee=user)
                # Record referral
                from accounts.models import Referral
                Referral.objects.create(inviter=inviter, invitee=user, used_referral_code=referral_code)
        return user


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField()
    new_password = serializers.CharField()
    confirm_password = serializers.CharField()

    def validate(self, data):
        if data.get("new_password") != data.get("confirm_password"):
            raise serializers.ValidationError("Passwords do not match")
        return data


class ResetPasswordSerializer(serializers.Serializer):
    phone = serializers.CharField()
    new_password = serializers.CharField()
    confirm_password = serializers.CharField()

    def validate(self, data):
        if not User.objects.filter(phone=data.get("phone")).exists():
            raise serializers.ValidationError("Phone does not exist")
        return data


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ["id", "product", "image", "created_at"]
        read_only_fields = ["id", "created_at"]


class PosibleFeatureValueSerializer(serializers.ModelSerializer):
    class Meta:
        model = PosibleFeatureValue
        fields = ["id", "feature", "value", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class FeatureSerializer(serializers.ModelSerializer):
    """Serializer for features, optionally including their possible values."""

    values = PosibleFeatureValueSerializer(many=True, read_only=True)

    class Meta:
        model = Feature
        fields = "__all__"


class ProductFeatureSerializer(serializers.ModelSerializer):
    """Read serializer for product features, expanding the feature details."""

    feature = FeatureSerializer(read_only=True)

    class Meta:
        model = ProductFeature
        fields = ["id", "product", "feature", "value", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class ProductFeatureCreateSerializer(serializers.ModelSerializer):
    """Write serializer for creating/updating product features.

    Validates that the provided value is one of the possible values
    defined for the selected feature.
    """

    class Meta:
        model = ProductFeature
        fields = ["id", "product", "feature", "value"]
        read_only_fields = ["id"]

    def validate(self, attrs):
        feature = attrs.get("feature")
        value = (attrs.get("value") or "").strip()
        if feature and value:
            if not PosibleFeatureValue.objects.filter(feature=feature, value=value).exists():
                raise serializers.ValidationError(
                    {"value": "Value must be one of the possible feature values for this feature."}
                )
        return attrs


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ['id', 'region', 'name', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

class ProductLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ['id', 'region', 'name']
        read_only_fields = ['id']

class ProductOwnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'phone', 'second_number', 'name', 'admin_verified', 'id_verified', 'level', 'avatar', 'business_logo', 'business_name']
        read_only_fields = ['id', 'email', 'phone', 'second_number', 'name', 'admin_verified', 'id_verified', 'level', 'avatar', 'business_logo', 'business_name']


class ProductSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    product_features = ProductFeatureSerializer(many=True, read_only=True)
    location = ProductLocationSerializer(read_only=True)
    location_id = serializers.PrimaryKeyRelatedField(
        queryset=Location.objects.filter(is_active=True),
        source='location',
        write_only=True,
        required=False,
        allow_null=True,
    )
    owner = ProductOwnerSerializer(read_only=True)
    favourited_by_user = serializers.SerializerMethodField(read_only=True)
    multiplier = serializers.SerializerMethodField(read_only=True)
    liked_by_user = serializers.SerializerMethodField(read_only=True)
    total_likes = serializers.SerializerMethodField(read_only=True)
    total_favourites = serializers.SerializerMethodField(read_only=True)
    total_reviews = serializers.SerializerMethodField(read_only=True)
    average_rating = serializers.SerializerMethodField(read_only=True)
    total_reports = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Product
        fields = "__all__"

    def get_multiplier(self, obj) -> float:
        sub = UserSubscription.objects.filter(user=obj.owner, is_active=True).order_by('-created_at').first()
        if sub and sub.subscription:
            return sub.subscription.multiplier
        return 1.0

    def get_favourited_by_user(self, obj) -> bool:
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if not user or not getattr(user, 'is_authenticated', False):
            return False
        return obj.favourited_by.filter(user=user).exists()

    def get_liked_by_user(self, obj) -> bool:
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if not user or not getattr(user, 'is_authenticated', False):
            return False
        return obj.liked_by.filter(user=user).exists()

    def get_total_likes(self, obj) -> int:
        return obj.liked_by.count()

    def get_total_favourites(self, obj) -> int:
        return obj.favourited_by.count()

    def get_total_reviews(self, obj) -> int:
        return obj.reviews.count()

    def get_average_rating(self, obj) -> str | None:
        from django.db.models import Avg
        agg = obj.reviews.aggregate(avg=Avg('rating'))
        avg = agg.get('avg')
        if avg is None:
            return None
        return f"{avg:.1f}"

    def get_total_reports(self, obj) -> int:
        return obj.reports.count()


class FeedbackSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Feedback
        fields = ['id', 'user', 'rating', 'message', 'created_at']
        read_only_fields = ['id', 'user', 'created_at']


class ProductReportSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    product = ProductSerializer(read_only=True)

    class Meta:
        model = ProductReport
        fields = ['id', 'product', 'user', 'reason', 'message', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = "__all__"


class SubCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = SubCategory
        fields = "__all__"


class AdminCategoryWithSubcategoriesSerializer(serializers.ModelSerializer):
    subcategories = SubCategorySerializer(many=True, read_only=True)

    class Meta:
        model = Category
        fields = ["id", "name", "description", "subcategories"]


class MessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)

    class Meta:
        model = Message
        fields = ["id", "room", "sender", "content", "created_at", "is_read"]


class ChatRoomSerializer(serializers.ModelSerializer):
    members = UserSerializer(many=True, read_only=True)
    messages = MessageSerializer(many=True, read_only=True)
    total_unread = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ChatRoom
        fields = ["id", "room_id", "name", "is_group", "members", "messages", "created_at", "total_unread"]

    def get_total_unread(self, obj) -> int:
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if user and hasattr(obj, "get_total_unread_messages"):
            return obj.get_total_unread_messages(user)
        return 0
    
class ReviewSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    product = ProductSerializer(read_only=True)
    likes_count = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Review
        fields = ['id', 'user', 'product', 'rating', 'comment', 'created_at', 'likes_count']
        read_only_fields = ['id', 'created_at', 'likes_count']

    def get_likes_count(self, obj) -> int:
        return obj.likes.count()

class CreateReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ['product', 'rating', 'comment']

    def validate(self, attrs):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        product = attrs.get('product')
        if user and getattr(user, 'is_authenticated', False) and product:
            if Review.objects.filter(user=user, product=product).exists():
                raise serializers.ValidationError('You have already reviewed this product.')
        return attrs


class CouponSerializer(serializers.ModelSerializer):
    remaining_uses = serializers.SerializerMethodField()

    class Meta:
        model = Coupon
        fields = [
            'id', 'code', 'description', 'discount_type', 'discount_value',
            'max_uses', 'uses', 'per_user_limit', 'valid_from', 'valid_until',
            'is_active', 'created_at', 'updated_at', 'remaining_uses'
        ]
        read_only_fields = ['id', 'uses', 'created_at', 'updated_at']

    def get_remaining_uses(self, obj) -> int | None:
        return obj.remaining_uses()


class CouponBroadcastRequestSerializer(serializers.Serializer):
    """Admin broadcast request body for sharing a coupon with users."""

    user_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=False,
        help_text='List of user IDs that should receive the coupon.',
    )


class CouponBroadcastResponseSerializer(serializers.Serializer):
    """Response payload for coupon broadcast."""

    status = serializers.CharField()
    coupon = serializers.CharField(help_text='Coupon code that was broadcast.')
    requested_user_ids = serializers.ListField(child=serializers.IntegerField(min_value=1))
    missing_user_ids = serializers.ListField(child=serializers.IntegerField(min_value=1))
    alerts_created = serializers.IntegerField(min_value=0)
    sms_queued = serializers.BooleanField()


class CouponRedemptionSerializer(serializers.ModelSerializer):
    coupon = CouponSerializer(read_only=True)

    class Meta:
        model = CouponRedemption
        fields = ['id', 'coupon', 'user', 'created_at']
        read_only_fields = ['id', 'created_at']


class SubscriptionSerializer(serializers.ModelSerializer):
    effective_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    features_list = serializers.ListField(child=serializers.CharField(), read_only=True)

    class Meta:
        model = Subscription
        fields = [
            'id', 'name', 'tier', 'description', 'price', 'original_price', 'multiplier',
            'discount_percentage', 'effective_price', 'features', 'features_list', 'duration_days',
            'max_products', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'effective_price', 'features_list']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Populate computed fields
        data['effective_price'] = str(instance.get_effective_price())
        data['features_list'] = instance.get_features_list()
        return data

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = [
            'id', 'user', 'subscription', 'amount', 'currency', 'provider',
            'reference', 'status', 'channel', 'raw_response',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'user', 'status', 'channel', 'raw_response', 'created_at', 'updated_at']

class UserSubscriptionSerializer(serializers.ModelSerializer):
    subscription = SubscriptionSerializer(read_only=True)
    payment = PaymentSerializer(read_only=True)
    subscription_id = serializers.PrimaryKeyRelatedField(
        queryset=Subscription.objects.filter(is_active=True),
        write_only=True,
        source='subscription'
    )

    class Meta:
        model = UserSubscription
        fields = ['id', 'subscription', 'subscription_id', 'payment', 'start_date', 'end_date', 'is_active', 'created_at']
        read_only_fields = ['id', 'subscription', 'payment', 'start_date', 'end_date', 'is_active', 'created_at']


class AccountDeleteRequestSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    class Meta:
        model = AccountDeleteRequest
        fields = ['id', 'reason', 'status', 'user', 'admin_comment', 'created_at', 'processed_at']
        read_only_fields = ['id', 'status', 'user', 'admin_comment', 'created_at', 'processed_at']


class PrivacyPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = PrivacyPolicy
        fields = ['id', 'title', 'date', 'body', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class TermsAndConditionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = TermsAndConditions
        fields = ['id', 'title', 'date', 'body', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class JobApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobApplication
        fields = [
            'id', 'application_id', 'name', 'email', 'phone',
            'location', 'gender', 'dob', 'resume', 'cover_letter',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'application_id', 'created_at', 'updated_at']




# ----- APIView documentation serializers -----

class PingResponseSerializer(serializers.Serializer):
    message = serializers.CharField()


class LoginResponseSerializer(serializers.Serializer):
    user = UserSerializer()
    token = serializers.CharField()


class RegisterUserResponseSerializer(serializers.Serializer):
    user = UserSerializer()
    token = serializers.CharField()


class GenericMessageSerializer(serializers.Serializer):
    message = serializers.CharField()


class SimpleStatusSerializer(serializers.Serializer):
    status = serializers.CharField()
    message = serializers.CharField(required=False, allow_blank=True)

class VerifyOTPGetRequestSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=10)


class VerifyOTPPostRequestSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=10)
    otp = serializers.CharField()


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            'email', 'phone', 'name', 'address', 'avatar',
            'preferred_notification_email', 'preferred_notification_phone'
        )
        extra_kwargs = {field: {"required": False} for field in fields}


class AdminToggleUserSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    is_active = serializers.BooleanField()


class AdminDeleteUserSerializer(serializers.Serializer):
    id = serializers.IntegerField()


class AdminReinstateCouponRedemptionSerializer(serializers.Serializer):
    """Admin request to unlock coupon redemption for users."""

    user_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=False,
        help_text='List of user IDs to reinstate coupon redemption for.'
    )


class AdminReinstateCouponRedemptionResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    requested_user_ids = serializers.ListField(child=serializers.IntegerField(min_value=1))
    missing_user_ids = serializers.ListField(child=serializers.IntegerField(min_value=1))
    updated_users = serializers.IntegerField(min_value=0)


class ChatroomIdResponseSerializer(serializers.Serializer):
    chatroom_id = serializers.CharField()


class RedeemReferralResponseSerializer(serializers.Serializer):
    redeemed_points = serializers.IntegerField()
    cash_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    remaining_points = serializers.IntegerField()
    wallet_balance = serializers.DecimalField(max_digits=10, decimal_places=2)

# --- Admin actions ---
class AdminVerifyUserSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    admin_verified = serializers.BooleanField(required=False, default=True)


class AdminChangeProductStatusSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    status = serializers.ChoiceField(choices=[tag.value for tag in ProductStatus])
    suspension_note = serializers.CharField(required=False, allow_blank=False)

    def validate(self, attrs):
        """Require suspension_note only when setting status to SUSPENDED.

        For all other statuses, the field remains optional.
        """
        status_value = attrs.get('status')
        note = attrs.get('suspension_note')
        if status_value == ProductStatus.SUSPENDED.value and not note:
            raise serializers.ValidationError({
                'suspension_note': 'This field is required when suspending a product.',
            })
        return attrs


class MarkAsTakenSerializer(serializers.Serializer):
    product = serializers.IntegerField()


class AlertSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        write_only=True,
    )

    class Meta:
        model = Alert
        fields = ['id', 'user', 'title', 'body', 'kind', 'is_read', 'created_at']
        read_only_fields = ['id', 'created_at']