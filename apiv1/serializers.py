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
)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        exclude = ["password", "groups", "user_permissions"]


class CreateUserSerializer(serializers.ModelSerializer):
    """Serializer for creating a user from admin panel"""

    class Meta:
        model = User
        fields = ["email", "phone", "name", "address", "avatar", "bio", "password"]
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
            bio=validated_data.get("bio"),
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
        fields = ["id", "product", "image", "uploaded_at"]
        read_only_fields = ["id", "uploaded_at"]


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
        fields = ["id", "room", "sender", "content", "timestamp", "is_read"]


class ChatRoomSerializer(serializers.ModelSerializer):
    members = UserSerializer(many=True, read_only=True)
    messages = MessageSerializer(many=True, read_only=True)
    total_unread = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ChatRoom
        fields = ["id", "room_id", "name", "is_group", "members", "messages", "created_at", "total_unread"]

    def get_total_unread(self, obj):
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