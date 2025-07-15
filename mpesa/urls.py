from django.urls import path
from .views import MpesaTokenView, MpesaSTKPushView

urlpatterns = [
    path('token/', MpesaTokenView.as_view()),
    path('stkpush/', MpesaSTKPushView.as_view()),
]
