"""
============================================================
PRODUCTION SETTINGS — Ishchi server muhiti
============================================================
Bu fayl faqat production serverda ishlatiladi.
Barcha maxfiy ma'lumotlar .env faylidan o'qiladi.

MUHIM: .env faylida quyidagilar bo'lishi SHART:
  SECRET_KEY, DB_NAME, DB_USER, DB_PASSWORD, DB_HOST,
  DB_PORT, REDIS_URL, ALLOWED_HOSTS
"""

from .base import *  # noqa: F401, F403
import os


# ============================================================
# XAVFSIZLIK (PRODUCTION UCHUN)
# ============================================================

# Production da DEBUG=False — xatolar foydalanuvchiga ko'rsatilmaydi
DEBUG = False

# .env dan maxfiy kalit olinadi
SECRET_KEY = os.environ['SECRET_KEY']

# Ruxsat etilgan hostlar (vergul bilan ajratilgan)
# Misol: .env da ALLOWED_HOSTS=crm.example.com,www.crm.example.com
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')


# ============================================================
# MA'LUMOTLAR BAZASI (PostgreSQL — production uchun)
# ============================================================

_DATABASE_URL = os.environ.get('DATABASE_URL')

if _DATABASE_URL:
    # Railway — DATABASE_URL formatida beradi (postgresql://user:pass@host/db)
    import dj_database_url  # noqa: E402 — faqat Railway muhitida o'rnatilgan
    DATABASES = {
        'default': dj_database_url.parse(
            _DATABASE_URL,
            conn_max_age=60,
            conn_health_checks=True,
        )
    }
else:
    # Docker Compose yoki boshqa muhit — alohida o'zgaruvchilar orqali
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ['DB_NAME'],
            'USER': os.environ['DB_USER'],
            'PASSWORD': os.environ['DB_PASSWORD'],
            'HOST': os.environ.get('DB_HOST', 'db'),
            'PORT': os.environ.get('DB_PORT', '5432'),
            'OPTIONS': {
                'connect_timeout': 10,
            },
            'CONN_MAX_AGE': 60,
        }
    }


# ============================================================
# KESH (Redis — production uchun)
# ============================================================

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL', 'redis://redis:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'SOCKET_CONNECT_TIMEOUT': 5,
            'SOCKET_TIMEOUT': 5,
        },
        'KEY_PREFIX': 'crm',  # Redis kalitlariga prefiks
        'TIMEOUT': 300,        # Standart kesh muddati: 5 daqiqa
    }
}

# Session ham Redis da saqlanadi
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'


# ============================================================
# XAVFSIZLIK SOZLAMALARI
# ============================================================

# HTTPS orqali yuborilgan cookie'larni himoya qilish
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True

# Xavfsiz sarlavhalar
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# HTTPS ga yo'naltirish (nginx HTTPS o'rnatilgandan keyin yoqing)
# SECURE_SSL_REDIRECT = True
# SECURE_HSTS_SECONDS = 31536000


# ============================================================
# CORS (Production da faqat frontend domeniga ruxsat)
# ============================================================

CORS_ORIGIN_ALLOW_ALL = False

# Ruxsat etilgan frontend domenlari
CORS_ORIGIN_WHITELIST = tuple(
    os.environ.get('CORS_ALLOWED_ORIGINS', 'http://localhost:5173').split(',')
)


# ============================================================
# STATIK FAYLLAR (WhiteNoise — Railway da nginx o'rniga)
# ============================================================

STATIC_ROOT = BASE_DIR / 'staticfiles'

MIDDLEWARE = [
    'config.middleware.HealthCheckMiddleware',     # BIRINCHI — health check ALLOWED_HOSTS dan oldin
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'


# ============================================================
# LOGGING — Xatolar va ogohlantirishlarni faylga yozish
# ============================================================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        # Railway da fayl tizimi vaqtinchalik — faqat konsolga yozamiz
        # (Railway dashboard da "Logs" bo'limida ko'rinadi)
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': True,
        },
    },
}


# ============================================================
# CELERY — Railway bepul rejimda worker yo'q, sinxron ishlaydi
# ============================================================

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True


# ============================================================
# SENTRY — Xatolarni kuzatish (ixtiyoriy)
# ============================================================

SENTRY_DSN = os.environ.get('SENTRY_DSN', '')

if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.celery import CeleryIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration(), CeleryIntegration()],
        traces_sample_rate=0.1,   # So'rovlarning 10% i kuzatiladi
        send_default_pii=False,   # Shaxsiy ma'lumotlarni yubormaydi
        environment='production',
    )
