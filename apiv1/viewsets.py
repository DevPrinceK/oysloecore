from rest_framework import permissions, viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response

from apiv1.models import (
    Category, SubCategory, Product, ProductImage,
    Feature, ProductFeature, Review, ChatRoom, Message
)
from apiv1.serializers import (
    CategorySerializer, SubCategorySerializer, ProductSerializer, ProductImageSerializer,
    FeatureSerializer, ProductFeatureSerializer, ReviewSerializer,
    ChatRoomSerializer, MessageSerializer
)


class IsAuthenticated(permissions.IsAuthenticated):
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
    permission_classes = [IsAuthenticated]
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
    queryset = ProductImage.objects.all().order_by('-uploaded_at')
    serializer_class = ProductImageSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['product']


class FeatureViewSet(viewsets.ModelViewSet):
    queryset = Feature.objects.all().order_by('name')
    serializer_class = FeatureSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['subcategory']


class ProductFeatureViewSet(viewsets.ModelViewSet):
    queryset = ProductFeature.objects.all()
    serializer_class = ProductFeatureSerializer
    permission_classes = [IsAuthenticated]
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
        user = self.request.user
        return Message.objects.filter(room__members=user).order_by('-timestamp')


class ChatRoomViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ChatRoomSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ChatRoom.objects.filter(members=self.request.user).order_by('-created_at')

    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        room = self.get_object()
        msgs = room.messages.order_by('timestamp')
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
