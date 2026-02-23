"""
============================================================
BASE SETTINGS — Barcha muhitlar uchun umumiy sozlamalar
============================================================
Bu fayl development va production da umumiy bo'lgan
barcha Django sozlamalarini o'z ichiga oladi.

local.py  → development uchun bu faylni extend qiladi
production.py → production uchun bu faylni extend qiladi
"""

from pathlib import Path
from datetime import timedelta
import os

# ============================================================
# ASOSIY YO'LLAR
# ============================================================

# Loyiha ildizi (shop_crm_system/)
BASE_DIR = Path(__file__).resolve().parent.parent.parent


# ============================================================
# O'RNATILGAN ILOVALAR (INSTALLED_APPS)
# ============================================================

INSTALLED_APPS = [
    # --- Django standart ilovalar ---
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # --- Uchinchi tomon kutubxonalar ---
    'rest_framework',                           # Django REST Framework
    'rest_framework_simplejwt',                 # JWT autentifikatsiya
    'rest_framework_simplejwt.token_blacklist', # Logout uchun token blacklist
    'corsheaders',                              # CORS (frontend bilan ishlash)
    'drf_yasg',                                 # Swagger / ReDoc API dokumentatsiya
    'django_filters',                           # Filterlash

    # --- Celery Beat (vazifalarni rejalashtirish) ---
    'django_celery_beat',

    # --- Mahalliy ilovalar ---
    'accaunt',    # Foydalanuvchilar, rollar, hodimlar
    'store',      # Do'kon, filial, ombor
    'trade',      # Savdo, chek, qaytarish
    'warehouse',  # Mahsulot, kategoriya, yetkazib beruvchi
    'expense',    # Xarajatlar
]


# ============================================================
# MIDDLEWARE
# ============================================================

MIDDLEWARE = [
    'config.middleware.HealthCheckMiddleware',     # BIRINCHI — health check ALLOWED_HOSTS dan oldin
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',       # CORS — CommonMiddleware DAN OLDIN bo'lishi shart
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


# ============================================================
# URL VA WSGI/ASGI
# ============================================================

ROOT_URLCONF = 'config.urls'
WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'


# ============================================================
# SHABLONLAR (TEMPLATES)
# ============================================================

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]


# ============================================================
# AUTENTIFIKATSIYA
# ============================================================

# Maxsus CustomUser modelimizni Django ga bildirish
AUTH_USER_MODEL = 'accaunt.CustomUser'

# Autentifikatsiya backend'lari (ketma-ketlik muhim)
AUTHENTICATION_BACKENDS = [
    # Bizning custom backend (username orqali autentifikatsiya)
    'accaunt.backend.CustomBackend',
    # Django standart backend (superadmin uchun)
    'django.contrib.auth.backends.ModelBackend',
]

# Parol validatsiya qoidalari
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# ============================================================
# JWT SOZLAMALARI (Simple JWT)
# ============================================================

SIMPLE_JWT = {
    # Access token muddati — 60 daqiqa
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),

    # Refresh token muddati — 3 kun
    'REFRESH_TOKEN_LIFETIME': timedelta(days=3),

    # Refresh tokendan foydalanganda yangi token yaratiladi
    'ROTATE_REFRESH_TOKENS': True,

    # Eski refresh token blacklist ga tushadi (logout uchun kerak)
    'BLACKLIST_AFTER_ROTATION': True,

    # Shifrlash algoritmi
    'ALGORITHM': 'HS256',

    # Token sarlavhasida "Bearer <token>" formatida yuboriladi
    'AUTH_HEADER_TYPES': ('Bearer',),

    # Token ichida foydalanuvchi ID si saqlanadigan kalit
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}


# ============================================================
# DJANGO REST FRAMEWORK SOZLAMALARI
# ============================================================

REST_FRAMEWORK = {
    # Standart ruxsat: faqat autentifikatsiya qilingan foydalanuvchilar
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],

    # JWT orqali autentifikatsiya
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],

    # So'rovlar chastotasini cheklash (Throttling)
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',  # Anonim foydalanuvchilar
        'rest_framework.throttling.UserRateThrottle',  # Autentifikatsiya qilinganlar
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '20/min',      # Anonim: minutiga 20 so'rov
        'user': '200/min',     # Foydalanuvchi: minutiga 200 so'rov
        'login': '5/min',      # Login: minutiga 5 urinish
        'register': '3/min',   # Ro'yxatdan o'tish: minutiga 3 ta
        'export': '5/min',     # Export: minutiga 5 ta
    },

    # Filtrlar backend'i
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],

    # Sahifalash (Pagination)
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,

    # Sana va vaqt formati
    'DATETIME_FORMAT': '%Y-%m-%d %H:%M:%S',
    'DATE_FORMAT': '%Y-%m-%d',
}


# ============================================================
# CORS SOZLAMALARI (Frontend bilan ishlash)
# ============================================================

# Ruxsat etilgan frontend manzillari
CORS_ORIGIN_WHITELIST = (
    'http://localhost:5173',   # Vue.js dev server (Vite)
    'http://localhost:8080',   # Vue.js dev server (Vue CLI)
    'http://localhost:3000',   # React (agar kerak bo'lsa)
)

# Ruxsat etilgan HTTP metodlar
CORS_ALLOW_METHODS = [
    'DELETE', 'GET', 'OPTIONS', 'PATCH', 'POST', 'PUT',
]

# Ruxsat etilgan sarlavhalar
CORS_ALLOW_HEADERS = [
    'accept', 'accept-encoding', 'authorization',
    'content-type', 'dnt', 'origin', 'user-agent',
    'x-csrftoken', 'x-requested-with',
]


# ============================================================
# SWAGGER / REDOC SOZLAMALARI (API Dokumentatsiya)
# ============================================================

SWAGGER_SETTINGS = {
    # Swagger UI da JWT token kiritish imkoniyati
    'SECURITY_DEFINITIONS': {
        'Bearer': {
            'type': 'apiKey',
            'name': 'Authorization',
            'in': 'header',
            'description': 'JWT Token. Misol: Bearer <token>',
        }
    },
    'USE_SESSION_AUTH': False,
    'JSON_EDITOR': True,
}


# ============================================================
# STATIK VA MEDIA FAYLLAR
# ============================================================

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'  # collectstatic uchun
STATICFILES_DIRS = []  # Qo'shimcha statik papkalar (kerak bo'lsa)

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'  # Yuklangan fayllar (rasm, PDF va h.k.)


# ============================================================
# XALQAROLASHTIRISH (I18N)
# ============================================================

LANGUAGE_CODE = 'uz'         # O'zbek tili
TIME_ZONE = 'Asia/Tashkent'  # O'zbekiston vaqt zonasi
USE_I18N = True
USE_TZ = True                # Timezone-aware datetimes


# ============================================================
# ID MAYDON TURI
# ============================================================

# Barcha modellarda birlamchi kalit avtomatik BigInt bo'ladi
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# ============================================================
# EMAIL SOZLAMALARI
# ============================================================

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER


# ============================================================
# CELERY SOZLAMALARI (Asinxron vazifalar)
# ============================================================

# Celery broker — Redis orqali ishlaydi
CELERY_BROKER_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

# Natijalar Redis da saqlanadi
CELERY_RESULT_BACKEND = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

# Celery Beat — rejalashtirilgan vazifalar (cron) uchun
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# Vaqt zonasi (Django bilan bir xil)
CELERY_TIMEZONE = TIME_ZONE

# Serializer — JSON formatida
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']
