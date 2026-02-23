# CLAUDE UCHUN ESLATMA — Yangi chatda bu faylni o'qi va davom et

## Sen kim bilan ishlayapsan
Foydalanuvchi: Ulugbek (Django dasturchisi)
Loyiha: `D:\projects\shop_crm_system` (GitHub: `UlugbekXatamjonov/shop_crm_system`, `main` branch)

## Loyiha nima
Django 5.2 REST API — Shop CRM tizimi (backend only, frontend yo'q).
Stack: DRF + SimpleJWT + Celery + Redis + PostgreSQL + Gunicorn.
Python 3.12. Dockerfile bor. docker-compose bor (local uchun).
Settings: `config/settings/base.py` → `local.py` (SQLite) / `production.py` (PostgreSQL+Redis).

---

## 23.02.2026 YANGILANISH — ASOSIY MUAMMO TOPILDI VA TUZATILDI

### Muammo: PORT mismatch
Railway o'zi `$PORT` o'zgaruvchisini tayinlaydi (masalan 3000). Lekin startCommand da
`--bind 0.0.0.0:8000` hardcode qilingan edi. Railway 3000 portga healthcheck yuborar,
gunicorn 8000 da tinglaydi → "service unavailable".

### Tuzatish qilingan fayllar:
- **`railway.toml`**: `--bind 0.0.0.0:8000` → `--bind 0.0.0.0:${PORT:-8000}`
- **`accaunt/migrations/0003_alter_worker_branch_verbose_name.py`**: Migration warning tuzatildi

### Commit: `f6bf1f3` — main branchga push qilindi

---

## BUGUN (21.02.2026) QILINGANLAR — HAMMASI TAYYOR

### Fayllar holati (main branch da, GitHub da):

**`requirements/production.txt`** ✅ — whitenoise==6.9.0 bor

**`config/settings/production.py`** ✅ — quyidagilar qo'shilgan:
- WhiteNoise MIDDLEWARE (SecurityMiddleware dan keyin)
- `STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'`
- LOGGING (faqat console, Railway uchun)
- `CELERY_TASK_ALWAYS_EAGER = True`
- `CELERY_TASK_EAGER_PROPAGATES = True`

**`Dockerfile`** ✅ — collectstatic BUILD vaqtida ishlaydi (dummy env bilan):
```dockerfile
RUN SECRET_KEY=dummy-build-secret-not-for-production \
    DATABASE_URL=postgres://u:p@localhost/db \
    python manage.py collectstatic --noinput --settings=config.settings.production
```

**`config/urls.py`** ✅ — health_check endpoint bor: `path('health/', health_check)`

**`requirements.txt`** (root) ✅ — `-r requirements/production.txt`

**`railway.toml`** ✅ — hozirgi holat:
```toml
[build]
builder = "DOCKERFILE"
dockerfilePath = "Dockerfile"

[deploy]
startCommand = "python manage.py migrate --settings=config.settings.production && gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 2 --timeout 120 --access-logfile - --error-logfile -"
healthcheckPath = "/health/"
healthcheckTimeout = 300
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 3
```

---

## Railway.app HOLATI

### Servislar (hammasi Online):
- **Postgres** ✅ Online
- **Redis** ✅ Online
- **shop_crm_system** ⚠️ — Hali deploy muvaffaqiyatli bo'lmagan

### Variables (to'g'ri sozlangan):
```
DJANGO_SETTINGS_MODULE=config.settings.production
DEBUG=False
ALLOWED_HOSTS=*
DATABASE_URL=${{Postgres.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}
CORS_ALLOWED_ORIGINS=http://localhost:5173
SECRET_KEY=<o'rnatilgan>
PORT=8000    ← BU QILINMAGAN, KEYINGI CHATDA QILISH KERAK!
```

---

## MUAMMO VA SABABI (bugun topildi)

### Asosiy muammo: `$PORT` Railway startCommand da expand bo'lmaydi
Deploy Logs da `PORT=$PORT` (literal dollar belgisi) chiqdi. Bu shuni bildiradi:
- Railway `startCommand` dagi `$PORT` ni shell variable sifatida tanímaydi
- Gunicorn qaysi portga bog'lanishni bilmaydi yoki noto'g'ri portga bog'lanadi
- Railway healthcheck port bilan mos kelmaydi → healthcheck failed

### Yechim (qo'llanildi):
- `railway.toml` da port **8000 ga hardcode qilindi**: `--bind 0.0.0.0:8000`
- Railway Variables ga `PORT=8000` qo'shish kerak (HALI QILINMAGAN!)

### Qo'shimcha muammo: `accaunt` app da migration yo'q model o'zgarishlar
```
Your models in app(s): 'accaunt' have changes that are not yet reflected in a migration
```
Bu warning hozirgacha deployni to'xtatmagan, lekin kelajakda muammo bo'lishi mumkin.
Lokal terminalda `python manage.py makemigrations accaunt` ishlatib migration yaratish kerak.
(Local da Celery o'rnatilmagan, shuning uchun avval: `pip install celery`)

---

## KEYINGI CHATDA NIMA QILISH KERAK

### 1-QADAM (eng muhim) — Railway Variables ga PORT qo'sh:
Railway → `shop_crm_system` → Variables → RAW Editor → qo'sh:
```
PORT=8000
```
→ "Update Variables" bosing → qayta deploy bo'ladi → Deploy Logs kuzating

### Muvaffaqiyatli deploy ko'rinishi:
```
Running migrations: No migrations to apply.
[INFO] Starting gunicorn 23.0.0
[INFO] Listening at: http://0.0.0.0:8000
[INFO] Booting worker with pid: ...
```

### 2-QADAM — Deploy muvaffaqiyatli bo'lgandan keyin:
1. **Domen olish**: Settings → Networking → "Generate Domain"
   - Misol: `fulfilling-nurturing.up.railway.app`
2. **ALLOWED_HOSTS yangilash**: Variables da:
   ```
   ALLOWED_HOSTS=fulfilling-nurturing.up.railway.app
   ```
3. **Superuser yaratish** (Railway CLI kerak):
   ```bash
   npm install -g @railway/cli
   railway login
   railway link
   railway run python manage.py createsuperuser
   ```
4. **Tekshirish**:
   - `https://sizning-domen.up.railway.app/health/` → "OK" ko'rinishi kerak
   - `https://sizning-domen.up.railway.app/admin/` → Login sahifasi
   - `https://sizning-domen.up.railway.app/swagger/` → API docs

### 3-QADAM — accaunt migration yaratish (ixtiyoriy, lekin tavsiya):
```bash
pip install celery
python manage.py makemigrations accaunt --settings=config.settings.local
git add accaunt/migrations/
git commit -m "feat: accaunt app migration qo'shildi"
git push origin main
```

---

## ARXIV: Bugun sinovdan o'tgan va rad etilgan yondashuvlar

1. `collectstatic` startCommand da → 5 daqiqa vaqt oldi, healthcheck o'tmadi
2. `$PORT` ni startCommand da ishlatish → Railway expand qilmaydi, literal `$PORT` ko'rsatadi
3. `migrate` hang qiladi degan taxmin → aslida PORT muammosi edi

---

## Loyiha tuzilmasi (muhim fayllar)
```
shop_crm_system/
├── config/
│   ├── __init__.py      ← Celery import (from .celery import app as celery_app)
│   ├── celery.py        ← Celery konfiguratsiya
│   ├── settings/
│   │   ├── base.py      ← Umumiy sozlamalar
│   │   ├── local.py     ← Development (SQLite)
│   │   └── production.py ← Production (PostgreSQL+Redis+WhiteNoise)
│   ├── urls.py          ← health_check endpoint bor
│   └── wsgi.py
├── accaunt/             ← CustomUser, rollar (⚠️ migration kerak)
├── store/               ← Do'kon, filial
├── trade/               ← Savdo
├── warehouse/           ← Mahsulot
├── expense/             ← Xarajatlar
├── requirements/
│   ├── base.txt         ← celery, django-redis, psycopg2 va boshqalar
│   └── production.txt   ← gunicorn, whitenoise, dj-database-url, sentry-sdk
├── requirements.txt     ← -r requirements/production.txt
├── Dockerfile           ← collectstatic BUILD vaqtida
└── railway.toml         ← port 8000 hardcode
```
