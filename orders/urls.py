from django.urls import path
from .views import (
    OrderCreateView,
    OrderByPhoneView,
    AllOrdersView,
    OrdersByDateView,
    LocationListCreateView,
    MpesaCallbackView,
    MpesaTransactionListView,
    MpesaTransactionByPhoneView,
    MonthlyEarningsView,
    LocationDetailView,
    MpesaStatusByCheckoutIDView,
)

urlpatterns = [
    path('create/', OrderCreateView.as_view(), name='order-create'),
    path('by-phone/', OrderByPhoneView.as_view(), name='order-by-phone'),
    path('all/', AllOrdersView.as_view(), name='all-orders'),
    path('by-date/', OrdersByDateView.as_view(), name='orders-by-date'),
    path('locations/', LocationListCreateView.as_view(), name='location-list'),
    path('locations/<int:id>/', LocationDetailView.as_view(), name='location-detail'),
    path('callback/', MpesaCallbackView.as_view(), name='mpesa-callback'),
    path('transactions/', MpesaTransactionListView.as_view(), name='mpesa-transactions'),
    path('transactions/by-phone/', MpesaTransactionByPhoneView.as_view(), name='mpesa-transactions-by-phone'),
    path("earnings/monthly/", MonthlyEarningsView.as_view()),
    path('status/', MpesaStatusByCheckoutIDView.as_view(), name='mpesa-status'),
]
