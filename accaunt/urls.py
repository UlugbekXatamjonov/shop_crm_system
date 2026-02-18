"""
============================================================
ACCAUNT APP — Auth URL'lari
============================================================
Faqat autentifikatsiya bilan bog'liq endpointlar.
Worker CRUD endpointlari → accaunt/api_urls.py da.

Prefix: /api/v1/auth/
"""

from django.urls import path
from .views import (
    UserRegistrationView,
    UserLoginView,
    LogoutAPIView,
    UserChangePasswordView,
    ProfileView,
)

urlpatterns = [
    # --- Ro'yxatdan o'tish ---
    path('register/', UserRegistrationView.as_view(), name='register'),

    # --- Tizimga kirish / chiqish ---
    path('login/',   UserLoginView.as_view(),   name='login'),
    path('logout/',  LogoutAPIView.as_view(),    name='logout'),

    # --- Parol ---
    path('change-password/', UserChangePasswordView.as_view(), name='change-password'),

    # --- Profil ---
    # ProfileView — RetrieveModelMixin + GenericViewSet
    # retrieve action → GET /api/v1/auth/profil/
    path('profil/', ProfileView.as_view({'get': 'retrieve'}), name='my-profile'),
]
