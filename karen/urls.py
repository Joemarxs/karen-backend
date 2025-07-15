from django.contrib import admin
from django.urls import path, include
from django.conf import settings  # ✅ add this
from django.conf.urls.static import static
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    path('admin/', admin.site.urls),

    # ✅ JWT Auth endpoints
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    path('api/', include('products.urls')),  # distinct prefix
    path('api/orders/', include('orders.urls')),      # distinct prefix
    path('api/mpesa/', include('mpesa.urls')),
    path('api/', include('emails.urls')), 

]


# ✅ Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
