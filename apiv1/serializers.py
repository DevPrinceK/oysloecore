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
    ProductFeature,
    Coupon,
    CouponRedemption,
    Feedback,
    Subscription,
    UserSubscription,
    Payment,
    AccountDeleteRequest,
)
from accounts.models import Location
from notifications.models import Alert
from oysloecore.sysutils.constants import ProductStatus


class UserSerializer(serializers.ModelSerializer):
    active_ads = serializers.IntegerField(read_only=True)
    taken_ads = serializers.IntegerField(read_only=True)
    class Meta:
        model = User
        exclude = ["password", "groups", "user_permissions"]


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


class FeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feature
        fields = "__all__"


class ProductFeatureSerializer(serializers.ModelSerializer):
    feature = FeatureSerializer(read_only=True)

    class Meta:
        model = ProductFeature
        fields = ["id", "product", "feature", "value"]


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
        fields = ['id', 'email', 'phone', 'name']
        read_only_fields = ['id', 'email', 'phone', 'name']


class ProductSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    product_features = ProductFeatureSerializer(many=True, read_only=True)
    location = ProductLocationSerializer(read_only=True)
    owner = ProductOwnerSerializer(read_only=True)

    class Meta:
        model = Product
        fields = "__all__"


class FeedbackSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Feedback
        fields = ['id', 'user', 'rating', 'message', 'created_at']
        read_only_fields = ['id', 'user', 'created_at']


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

    class Meta:
        model = Review
        fields = ['id', 'user', 'product', 'rating', 'comment', 'created_at']
        read_only_fields = ['id', 'created_at']

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
    class Meta:
        model = AccountDeleteRequest
        fields = ['id', 'reason', 'status', 'admin_comment', 'created_at', 'processed_at']
        read_only_fields = ['id', 'status', 'admin_comment', 'created_at', 'processed_at']




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


class MarkAsTakenSerializer(serializers.Serializer):
    product = serializers.IntegerField()


class AlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = Alert
        fields = ['id', 'title', 'body', 'kind', 'is_read', 'created_at']
        read_only_fields = ['id', 'created_at']