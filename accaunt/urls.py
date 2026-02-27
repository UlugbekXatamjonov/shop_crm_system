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
    SendPasswordResetEmailView,
    UserPasswordResetView,
    ProfileView,
)

urlpatterns = [
    # --- Ro'yxatdan o'tish ---
    path('register/', UserRegistrationView.as_view(), name='register'),

    # --- Tizimga kirish / chiqish ---
    path('login/',   UserLoginView.as_view(),   name='login'),
    path('logout/',  LogoutAPIView.as_view(),    name='logout'),

    # --- Parol ---
    path('change-password/',   UserChangePasswordView.as_view(),     name='change-password'),
    path('send-reset-email/',  SendPasswordResetEmailView.as_view(), name='send-reset-email'),
    path('reset-password/<str:uid>/<str:token>/', UserPasswordResetView.as_view(), name='reset-password'),

    # --- Profil ---
    # GET   /api/v1/auth/profil/ — profilni ko'rish
    # PATCH /api/v1/auth/profil/ — ism, familiya, telefon yangilash
    path('profil/', ProfileView.as_view({'get': 'retrieve', 'patch': 'partial_update'}), name='my-profile'),
]
