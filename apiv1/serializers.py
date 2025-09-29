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
)


class UserSerializer(serializers.ModelSerializer):
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
    class Meta:
        model = User
        fields = ("email", "phone", "password", "name", "address")
        extra_kwargs = {"password": {"write_only": True}, "email": {"required": True}, "phone": {"required": True}}

    def validate(self, attrs):
        if User.objects.filter(email=attrs.get("email")).exists():
            raise serializers.ValidationError("Email already exists")
        if User.objects.filter(phone=attrs.get("phone")).exists():
            raise serializers.ValidationError("Phone already exists")
        return attrs

    def create(self, validated_data):
        return User.objects.create_user(
            phone=validated_data.get("phone"),
            email=validated_data.get("email"),
            password=validated_data.get("password"),
            name=validated_data.get("name"),
            address=validated_data.get("address"),
        )


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField()
    new_password = serializers.CharField()
    confirm_password = serializers.CharField()

    def validate(self, data):
        if data.get("new_password") != data.get("confirm_password"):
            raise serializers.ValidationError("Passwords do not match")
        return data


class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.CharField()
    new_password = serializers.CharField()
    confirm_password = serializers.CharField()

    def validate(self, data):
        if not User.objects.filter(email=data.get("email")).exists():
            raise serializers.ValidationError("Email does not exist")
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


class ProductSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    product_features = ProductFeatureSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = "__all__"


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = "__all__"


class SubCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = SubCategory
        fields = "__all__"


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


class VerifyOTPPostRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()
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