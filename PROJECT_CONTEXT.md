# CLAUDE UCHUN ESLATMA — Yangi chatda bu faylni o'qi va davom et

## Sen kim bilan ishlayapsan
Foydalanuvchi: Ulugbek (Django dasturchisi)
Loyiha: `D:\projects\shop_crm_system` (GitHub: `UlugbekXatamjonov/shop_crm_system`, `main` branch)

## Loyiha nima
Django 5.2 REST API — Shop CRM tizimi (backend only, frontend yo'q).
Stack: DRF + SimpleJWT + Celery + Redis + PostgreSQL + Gunicorn.
Python 3.12. Dockerfile bor. docker-compose bor (local uchun).
Settings: `config/settings/base.py` → `local.py` (SQLite) / `production.py` (PostgreSQL+Redis).

## Bu chatda nima gaplashildi
1. Loyihani PythonAnywhere ga yuklab bo'lmasligini aniqladik (Celery/Redis yo'q, PostgreSQL yo'q).
2. **Railway.app** — eng yaxshi bepul variant deb qaror qildik (real foydalanish uchun).
3. Railway uchun loyihada nima o'zgartirilishi kerakligini to'liq aniqladik.
4. Hali hech qanday fayl o'zgartirilmagan — hammasi faqat rejalashtirildi.

## Keyingi chat da nima qilish kerak
**"Keling fayllarni o'zgartiramiz" de va quyidagi 6 ta ishni bajara boshlang:**

### ISH 1 — `requirements/production.txt` ga qo'sh
```
whitenoise==6.9.0
```

### ISH 2 — `config/settings/production.py` fayl OXIRIGA qo'sh
```python
# WhiteNoise — Railway da nginx o'rniga statik fayllar uchun
MIDDLEWARE = [
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

# Railway da fayl yo'q — faqat konsol logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {'console': {'class': 'logging.StreamHandler'}},
    'loggers': {'django': {'handlers': ['console'], 'level': 'ERROR'}},
}

# Celery worker yo'q (Railway bepul rejim) — sinxron ishlaydi
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
```

### ISH 3 — `Dockerfile` da 2 ta o'zgartirish
- Bu qatorni **O'CHIR** (SECRET_KEY yo'qligi sababli build da xato beradi):
  `RUN python manage.py collectstatic --noinput --settings=config.settings.production || true`
- Bu qatorni **O'ZGARTIR**:
  `RUN mkdir -p logs && chown -R appuser:appuser /app`
  → `RUN chown -R appuser:appuser /app`

### ISH 4 — `config/urls.py` ga health check qo'sh
```python
from django.http import HttpResponse

def health_check(request):
    return HttpResponse("OK", content_type="text/plain", status=200)
```
`urlpatterns` ga birinchi qilib: `path('health/', health_check, name='health-check'),`

### ISH 5 — Root da yangi `requirements.txt` fayl yarat
```
-r requirements/production.txt
```

### ISH 6 — Root da yangi `railway.toml` fayl yarat
```toml
[build]
builder = "DOCKERFILE"
dockerfilePath = "Dockerfile"

[deploy]
startCommand = "python manage.py migrate --settings=config.settings.production && python manage.py collectstatic --noinput --settings=config.settings.production && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 120 --access-logfile - --error-logfile -"
healthcheckPath = "/health/"
healthcheckTimeout = 300
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 3
```

---

## Fayllar o'zgartirilgandan keyin (Railway.app sozlash)
Bu qismni foydalanuvchiga bosqichma-bosqich tushuntir:
1. `railway.app` → GitHub bilan ro'yxatdan o'tish
2. New Project → Empty Project
3. + New Service → Database → PostgreSQL
4. + New Service → Database → Redis
5. + New Service → GitHub Repo → `main` branch
6. Web service Variables tab ga quyidagilarni qo'sh:

```
SECRET_KEY=<generatsiya: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())">
DJANGO_SETTINGS_MODULE=config.settings.production
DEBUG=False
ALLOWED_HOSTS=*
DB_NAME=${{Postgres.PGDATABASE}}
DB_USER=${{Postgres.PGUSER}}
DB_PASSWORD=${{Postgres.PGPASSWORD}}
DB_HOST=${{Postgres.PGHOST}}
DB_PORT=${{Postgres.PGPORT}}
REDIS_URL=${{Redis.REDIS_URL}}
CORS_ALLOWED_ORIGINS=http://localhost:5173
```

7. Deploy bo'lgandan keyin `ALLOWED_HOSTS` ni haqiqiy Railway domeniga yangilash (masalan `myapp.up.railway.app`)
8. Superuser: `railway run python manage.py createsuperuser`
