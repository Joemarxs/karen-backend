from django.urls import path
from .views import (
    ProductListView,
    CategoryListView,
    ProductCreateView,
    ProductDetailView,
    CategoryCreateView,
    CategoryDetailView,
    ProductFrontendListView
)

urlpatterns = [
    path('products/', ProductListView.as_view(), name='product-list'),
    path('categories/', CategoryListView.as_view(), name='category-list'),

    # Admin routes
    path('products/create/', ProductCreateView.as_view(), name='product-create'),
    path('products/<int:id>/', ProductDetailView.as_view(), name='product-detail'),
    path('categories/create/', CategoryCreateView.as_view(), name='category-create'), 
    path('categories/<int:id>/', CategoryDetailView.as_view(), name='category-detail'),
    path('frontend/products/', ProductFrontendListView.as_view(), name='frontend-product-list'),# ← New route
    path('frontend/products/<int:id>/', ProductFrontendListView.as_view(), name='product-frontend-detail'),
]
