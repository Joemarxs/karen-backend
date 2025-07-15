# emails/urls.py
from django.urls import path
from .views import book_tour_view

urlpatterns = [
    path('book-tour/', book_tour_view),
]
