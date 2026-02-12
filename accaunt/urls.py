# ❌ urls.py butunlay bo'sh, hech qanday URL yo'q
# ✅ Kamida quyidagilar bo'lishi kerak:

from django.urls import path
from .views import (
    UserRegistrationView, UserLoginView, LogoutAPIView,
    UserChangePasswordView, SendPasswordResetEmailView, UserPasswordResetView,
    UserProfile_View
)

urlpatterns = [
    path('register/', UserRegistrationView.as_view(), name='register'),
    path('login/', UserLoginView.as_view(), name='login'),
    path('logout/', LogoutAPIView.as_view(), name='logout'),
    path('change-password/', UserChangePasswordView.as_view(), name='change-password'),
    # path('send-reset-email/', SendPasswordResetEmailView.as_view(), name='send-reset-email'),
    # path('reset-password/<uid>/<token>/', UserPasswordResetView.as_view(), name='reset-password'),
    path('profil/', UserProfile_View.as_view({'get': 'list'}), name='profil/'),

]


