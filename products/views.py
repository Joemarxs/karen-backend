from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Product, Category
from .serializers import ProductSerializer, CategorySerializer, ProductFrontendSerializer
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from .permissions import IsAdminUserOnly
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q



class ProductPagination(PageNumberPagination):
    page_size = 20

class ProductFrontendListView(APIView):
    def get(self, request, id=None):
        if id is not None:
            product = get_object_or_404(Product, id=id)
            serializer = ProductFrontendSerializer(product, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        products = Product.objects.all()
        serializer = ProductFrontendSerializer(products, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class CategoryDetailView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUserOnly]

    def put(self, request, id):
        category = get_object_or_404(Category, id=id)
        serializer = CategorySerializer(category, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, id):
        category = get_object_or_404(Category, id=id)
        category.delete()
        return Response({"message": "Category deleted successfully."}, status=status.HTTP_204_NO_CONTENT)


class CategoryCreateView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUserOnly]

    def post(self, request):
        serializer = CategorySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProductListView(APIView):
    def get(self, request):
        category_slug = request.GET.get('category')
        sort_by = request.GET.get('sort')
        search = request.GET.get('search')  

        products = Product.objects.all()

        if category_slug:
            products = products.filter(category__slug=category_slug)

        if search:
            products = products.filter(
                Q(name__icontains=search) | Q(description__icontains=search)
            )

        if sort_by == "price_asc":
            products = products.order_by("price")
        elif sort_by == "price_desc":
            products = products.order_by("-price")
        elif sort_by == "name_asc":
            products = products.order_by("name")
        elif sort_by == "name_desc":
            products = products.order_by("-name")

        paginator = ProductPagination()
        paginated_products = paginator.paginate_queryset(products, request)
        serializer = ProductSerializer(paginated_products, many=True, context={"request": request})
        return paginator.get_paginated_response(serializer.data)

class CategoryListView(APIView):
    def get(self, request):
        categories = Category.objects.all()
        serializer = CategorySerializer(categories, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ProductCreateView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUserOnly]

    def post(self, request):
        serializer = ProductSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProductDetailView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUserOnly]

    def get_object(self, id):
        try:
            return Product.objects.get(id=id)
        except Product.DoesNotExist:
            return None

    def get(self, request, id):
        product = self.get_object(id)
        if not product:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = ProductSerializer(product)
        return Response(serializer.data)

    def put(self, request, id):
        product = self.get_object(id)
        if not product:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = ProductSerializer(product, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, id):
        product = self.get_object(id)
        if not product:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        product.delete()
        return Response({"detail": "Deleted"}, status=status.HTTP_204_NO_CONTENT)
    