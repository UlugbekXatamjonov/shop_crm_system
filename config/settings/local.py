"""
============================================================
LOCAL SETTINGS — Development (ishlab chiqish) muhiti
============================================================
Bu fayl faqat lokal kompyuterda ishlab chiqish vaqtida ishlatiladi.
SQLite ma'lumotlar bazasi, DEBUG rejimi yoqilgan.

ESLATMA: Bu fayl git ga push qilinadi, lekin maxfiy ma'lumotlar yo'q.
"""

from .base import *  # noqa: F401, F403 — barcha asosiy sozlamalarni olamiz


# ============================================================
# XAVFSIZLIK (DEVELOPMENT UCHUN)
# ============================================================

# Development da DEBUG=True — xatolar to'liq ko'rsatiladi
DEBUG = True

# Barcha hostlarga ruxsat (local server uchun)
ALLOWED_HOSTS = ['*']

# Development SECRET_KEY (production da .env dan olinadi)
SECRET_KEY = 'django-insecure-dev-key-for-local-use-only-change-in-production'


# ============================================================
# MA'LUMOTLAR BAZASI (SQLite — development uchun)
# ============================================================

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        # db.sqlite3 fayli loyiha ildizida yaratiladi
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# ============================================================
# KESH (Development da kesh o'chirilgan — har so'rovda yangi)
# ============================================================

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}


# ============================================================
# EMAIL (Development da konsolga chiqaradi)
# ============================================================

# Development da email yuborish o'rniga konsolga chiqaradi
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'


# ============================================================
# CORS (Development da barcha originlarga ruxsat)
# ============================================================

# Development da barcha frontend manzillariga ruxsat
CORS_ORIGIN_ALLOW_ALL = True


# ============================================================
# CELERY (Development da sinxron rejimda)
# ============================================================

# Development da Celery vazifalar sinxron bajariladi
# (Redis o'rnatilmagan bo'lsa ham ishlaydi)
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
