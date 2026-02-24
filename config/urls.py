"""
============================================================
LOYIHA URL KONFIGURATSIYASI
============================================================
Barcha app URL'lari shu yerda birlashtiriladi.

URL tuzilmasi:
  /admin/                       — Django admin panel
  /api/v1/auth/                 — Autentifikatsiya (accaunt.urls)
  /api/v1/                      — Worker CRUD (accaunt.api_urls)
  /swagger/                     — Swagger UI (development)
  /redoc/                       — ReDoc UI (development)

❗ Deployment da swagger/redoc ni yopib qo'yish kerak
   (permission_classes = IsAuthenticated)
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse


def health_check(request):
    return HttpResponse("OK", content_type="text/plain", status=200)

from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

# ============================================================
# SWAGGER / REDOC KONFIGURATSIYA
# ============================================================

schema_view = get_schema_view(
    openapi.Info(
        title="Shop CRM System API",
        default_version='v1',
        description=(
            "Do'kon boshqaruv tizimi (CRM) uchun REST API.\n\n"
            "Autentifikatsiya: JWT Bearer token.\n"
            "Authorization: Bearer <access_token>"
        ),
        terms_of_service="https://t.me/UlugbekKhatamjonov",
        contact=openapi.Contact(email="xatamjonovulugbek17@gmail.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    # ❗ Deploydan keyin IsAuthenticated ga o'zgartirish kerak
    permission_classes=(permissions.AllowAny,),
)

# ============================================================
# URL PATTERN'LAR
# ============================================================

urlpatterns = [
    # Railway health check
    path('health/', health_check, name='health-check'),

    # Django admin
    path('admin/', admin.site.urls),

    # --- API v1 ---
    # Autentifikatsiya: register, login, logout, change-password, profil
    path('api/v1/auth/', include('accaunt.urls')),

    # Worker CRUD: /api/v1/workers/
    path('api/v1/', include('accaunt.api_urls')),

    # Store va Branch CRUD: /api/v1/stores/, /api/v1/branches/
    path('api/v1/', include('store.api_urls')),

    # --- API Dokumentatsiya ---
    path('swagger<format>/', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/',         schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/',           schema_view.with_ui('redoc',   cache_timeout=0), name='schema-redoc'),
]

# ============================================================
# MEDIA VA STATIC (faqat development uchun)
# ============================================================

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,  document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
