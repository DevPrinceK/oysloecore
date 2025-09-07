from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apiv1.models import Category, Product, SubCategory
from apiv1.serializers import CategorySerializer, ProductSerializer, SubCategorySerializer


class CategoriesAPIView(APIView):
    '''API view to retrieve product categories'''
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        '''Get all product categories'''
        categories = Category.objects.all().order_by('name')
        serializer = CategorySerializer(categories, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    

class SubCategoriesAPIView(APIView):
    '''API view to retrieve product sub-categories'''
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        '''Get all product sub-categories'''
        subcategories = SubCategory.objects.all().order_by('name')
        serializer = SubCategorySerializer(subcategories, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    

class ProductsAPI(APIView):
    '''API view to retrieve products'''
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        '''Get all products'''
        # get 50 random products
        products = Product.objects.all().order_by('?')[:50]
        serializer = ProductSerializer(products, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    

class RelatedProductsAPI(APIView):
    '''API view to retrieve related products based on category'''
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        '''Get related products based on category'''
        category_id = request.query_params.get('category_id')
        products = Product.objects.filter(category__id=category_id).order_by('?')[:50]
        serializer = ProductSerializer(products, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)