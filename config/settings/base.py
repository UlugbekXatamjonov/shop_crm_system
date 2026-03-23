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

from celery.schedules import crontab

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
    'export',       # Export / Import (B16)
    'dashboard',    # Dashboard (B17)
    'subscription', # Obuna tizimi (B20)
    'superadmin',   # Super Admin Panel (B21-B23)
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
    'ACCESS_TOKEN_LIFETIME': timedelta(days=1), # keyinroq, loyiha tugaganda (minutes=60) qilamiz

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
    # ReadOnlyIfExpired — obuna tugagan do'konlar uchun faqat o'qish rejimi
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
        'accaunt.permissions.ReadOnlyIfExpired',
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
        'anon':           '20/min',   # Anonim: minutiga 20 so'rov
        'user':           '200/min',  # Foydalanuvchi: minutiga 200 so'rov
        'login':          '5/min',    # Login: minutiga 5 urinish (brute-force himoya)
        'register':       '3/min',    # Ro'yxatdan o'tish: minutiga 3 ta (spam himoya)
        'password_reset': '3/hour',   # Parol tiklash: soatiga 3 ta (email spam himoya)
        'export':         '10/min',   # Export Excel/PDF: minutiga 10 ta
        'bulk':           '20/min',   # Bulk operatsiyalar: minutiga 20 ta
    },

    # Filtrlar backend'i
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],

    # Sahifalash (Pagination)
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,

    # Sana va vaqt formati
    'DATETIME_FORMAT': '%Y-%m-%d | %H:%M',
    'DATE_FORMAT': '%Y-%m-%d',

    # O'zbek tilidagi xato xabarlari
    'EXCEPTION_HANDLER': 'config.exceptions.custom_exception_handler',
}


# ============================================================
# FRONTEND URL (parol tiklash havolasi uchun)
# ============================================================

FRONTEND_URL = os.environ.get('FRONTEND_URL', 'https://shop-crm-front.vercel.app')


# ============================================================
# CORS SOZLAMALARI (Frontend bilan ishlash)
# ============================================================

# Ruxsat etilgan frontend manzillari
CORS_ALLOWED_ORIGINS = [
    'http://localhost:5173',                    # Vue.js dev server (Vite)
    'http://localhost:8080',                    # Vue.js dev server (Vue CLI)
    'http://localhost:3000',                    # React (agar kerak bo'lsa)
    'https://shop-crm-front.vercel.app',        # Vercel production frontend
]

# Ruxsat etilgan HTTP metodlar
CORS_ALLOW_METHODS = [
    'DELETE', 'GET', 'OPTIONS', 'PATCH', 'POST', 'PUT',
]

# Ruxsat etilgan sarlavhalar
CORS_ALLOW_HEADERS = [
    'accept', 'accept-encoding', 'authorization',
    'content-type', 'dnt', 'origin', 'user-agent',
    'x-csrftoken', 'x-requested-with',
    'x-idempotency-key',  # Offline rejim uchun (BOSQICH 18)
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

# Rejalashtirilgan vazifalar (Celery Beat)
CELERY_BEAT_SCHEDULE = {
    # BOSQICH 1.4 — CBU API dan valyuta kurslarini har kuni 09:00 da yangilash
    'update-exchange-rates-daily': {
        'task':     'warehouse.tasks.update_exchange_rates',
        'schedule': crontab(hour=9, minute=0),  # Har kuni soat 09:00 da
        'options': {
            'expires': 3600,  # 1 soat ichida bajarilmasa — bekor qilinadi
        },
    },

    # BOSQICH 15 — Kam qoldiq mahsulotlarni har 6 soatda tekshirish
    'check-low-stock-every-6h': {
        'task':     'warehouse.tasks.check_low_stock',
        'schedule': crontab(hour='0,6,12,18', minute=0),  # 00:00, 06:00, 12:00, 18:00
        'options': {
            'expires': 21600,  # 6 soat ichida bajarilmasa — bekor qilinadi
        },
    },

    # BOSQICH 15 — Har oy 1-kuni yangi WorkerKPI yozuvlarini yaratish
    'generate-monthly-worker-kpi': {
        'task':     'accaunt.tasks.generate_monthly_worker_kpi',
        'schedule': crontab(hour=0, minute=1, day_of_month=1),  # Har oy 1-kuni 00:01
        'options': {
            'expires': 3600,  # 1 soat ichida bajarilmasa — bekor qilinadi
        },
    },

    # BOSQICH 20 — Har kuni 00:01 da obuna muddatlarini tekshirish
    'check-subscription-expiry-daily': {
        'task':     'subscription.tasks.check_subscription_expiry',
        'schedule': crontab(hour=0, minute=1),   # Har kuni 00:01
        'options': {
            'expires': 3600,  # 1 soat ichida bajarilmasa — bekor qilinadi
        },
    },
}

# ============================================================
# SUBSCRIPTION SOZLAMALARI (B20)
# ============================================================

# Sinov davri kunlari — signals.py da ishlatiladi
SUBSCRIPTION_TRIAL_DAYS = 30

# Ogohlantirish kunlari — tasks.py da ishlatiladi
SUBSCRIPTION_EXPIRY_NOTIFY = [10, 3, 1]

# Redis kesh TTL (soniya) — cache_utils.py da ishlatiladi
SUBSCRIPTION_CACHE_TTL = 3600  # 1 soat

# ============================================================
# UMUMIY CHEKLOVLAR
# ============================================================

# Bir so'rovda maksimal QR/barcode bosib chiqarish soni — warehouse/views.py
QR_BULK_MAX_PRODUCTS = 500
