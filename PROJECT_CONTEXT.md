# CLAUDE UCHUN ESLATMA — Yangi chatda bu faylni o'qi va davom et

## Sen kim bilan ishlayapsan
Foydalanuvchi: Ulugbek (Django dasturchisi)
Loyiha: `C:\Users\U17\my_projects\shop_crm_system` (GitHub: `UlugbekXatamjonov/shop_crm_system`, `main` branch)

## Loyiha nima
Django 5.2 REST API — Shop CRM tizimi (backend only, frontend yo'q).
Stack: DRF + SimpleJWT + Celery + Redis + PostgreSQL + Gunicorn.
Python 3.12. Dockerfile bor. docker-compose bor (local uchun).
Settings: `config/settings/base.py` → `local.py` (SQLite) / `production.py` (PostgreSQL+Redis).

---

## LOYIHA HOLATI (24.02.2026)

| App         | Holat              | Izoh                                          |
|-------------|-------------------|-----------------------------------------------|
| `accaunt`   | ✅ Tugallangan     | CustomUser, Worker, AuditLog, JWT auth        |
| `store`     | ✅ Tugallangan     | Store, Branch CRUD (soft delete, multi-tenant)|
| `warehouse` | ❌ Boshlanmagan   | Navbatda                                      |
| `trade`     | ❌ Boshlanmagan   | Navbatda                                      |
| `expense`   | ❌ Boshlanmagan   | Navbatda                                      |

---

## STANDART RESPONSE PATTERN (BARCHA APPLACATION)

Barcha write operatsiyalarda shu pattern ishlatiladi:

| Metod      | Status | Javob formati                          |
|------------|--------|----------------------------------------|
| `create`   | 201    | `{'message': '...', 'data': {...}}`    |
| `update`   | 200    | `{'message': '...', 'data': {...}}`    |
| `destroy`  | 200    | `{'message': '...'}`                   |
| `list`     | 200    | faqat `[...]` (message yo'q)           |
| `retrieve` | 200    | faqat `{...}` (message yo'q)           |

---

## 24.02.2026 QILINGAN ISHLAR

### 1. `store/views.py` — message+data pattern joriy qilindi
- `StoreViewSet.create()` → `{'message': ..., 'data': ...}` (avval faqat data edi)
- `StoreViewSet.update()` → yangi metod qo'shildi (avval yo'q edi)
- `BranchViewSet.create()` → `{'message': ..., 'data': ...}` (avval faqat data edi)
- `BranchViewSet.update()` → yangi metod qo'shildi (avval yo'q edi)
- Commit: `19125a9`

### 2. `accaunt/views.py` — WorkerViewSet yangilandi
- `WorkerViewSet.create()` → `'worker'` key → `'data'` key ga o'zgartirildi
- `WorkerViewSet.update()` → yangi metod: message+data+AuditLog (partial=True)
- `WorkerViewSet.destroy()` → yangi metod: message qaytaradi (200 OK)
- `WorkerViewSet.perform_destroy()` → AuditLog.DELETE qo'shildi
- Commit: `acc1d9f`

### 3. `memory/patterns.md` — yangilandi
- `create() / update() response pattern` bo'limi to'liq qayta yozildi
- `update()` pattern qo'shildi
- Qoida yozildi: write → `message+data`, read → faqat `data`

---

## 23.02.2026 QILINGANLAR

### Railway PORT muammosi hal qilindi
- `railway.toml`: `--bind 0.0.0.0:8000` hardcode (PORT expand bo'lmaydi)
- Commit: `f6bf1f3`

---

## 21.02.2026 QILINGANLAR

### Production deploy sozlamalari
- `requirements/production.txt` — whitenoise qo'shildi
- `config/settings/production.py` — WhiteNoise, LOGGING, Celery eager
- `Dockerfile` — `collectstatic` BUILD vaqtida ishlaydi
- `config/urls.py` — `/health/` endpoint
- `railway.toml` — port 8000 hardcode, healthcheckPath

---

## RAILWAY DEPLOY HOLATI

```toml
# railway.toml (hozirgi)
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

**Railway Variables (to'g'ri sozlangan):**
```
DJANGO_SETTINGS_MODULE=config.settings.production
DEBUG=False
ALLOWED_HOSTS=*
DATABASE_URL=${{Postgres.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}
SECRET_KEY=<o'rnatilgan>
PORT=8000
```

**Deploy URL:** https://shopcrmsystem-production.up.railway.app/

---

## KEYINGI ISHLAR (navbat)

### `warehouse` app — to'liq qurish kerak
Modellar (patterns.md ga ko'ra):
- `Category` — mahsulot kategoriyasi
- `Product` — mahsulot (nom, kategoriya, birlik, narx, shtrix-kod)
- `Stock` — filial bo'yicha qoldiq (Product + Branch + miqdor)
- `StockMovement` — kirim/chiqim tarixi

Endpointlar:
- `GET/POST /api/v1/warehouse/categories/`
- `GET/POST /api/v1/warehouse/products/`
- `GET/POST /api/v1/warehouse/stocks/`
- `GET/POST /api/v1/warehouse/movements/`

### `trade` app — to'liq qurish kerak
- `Sale` — sotuv (Branch, Worker, vaqt, jami summa)
- `SaleItem` — sotuv tarkibi (Sale, Product, miqdor, narx)

### `expense` app — to'liq qurish kerak
- `ExpenseCategory` — xarajat kategoriyasi
- `Expense` — xarajat (Branch, Worker, miqdor, izoh, sana)

---

## MUHIM ESLATMALAR

### Worktree pattern (MAJBURIY)
- Claude worktree da ishlaydi: `.claude/worktrees/thirsty-cori/`
- Har o'zgarishdan keyin: `cp worktree/* → main` → `git add` → `git commit`
- `__pycache__` va `db.sqlite3` ni HECH QACHON commit qilma

### Virtual env
```bash
source /c/Users/U17/my_projects/shop_crm_system/myenv/Scripts/activate
```

### Migration yaratish (non-interactive)
```bash
printf "1\n\n1\n\n" | python manage.py makemigrations appname --settings=config.settings.local
```

### Git log (so'nggi commitlar)
```
acc1d9f  feat(accaunt): WorkerViewSet update/destroy metodlari va message+data pattern
19125a9  feat(store): create/update javoblariga message+data qo'shildi
f6bf1f3  fix(railway): PORT mismatch tuzatildi
```

---

## LOYIHA TUZILMASI

```
shop_crm_system/
├── config/
│   ├── __init__.py      ← Celery import
│   ├── celery.py        ← Celery konfiguratsiya
│   ├── settings/
│   │   ├── base.py      ← Umumiy sozlamalar
│   │   ├── local.py     ← Development (SQLite)
│   │   └── production.py ← Production (PostgreSQL+Redis+WhiteNoise)
│   ├── urls.py          ← /health/ endpoint bor
│   └── wsgi.py
├── accaunt/             ✅ CustomUser, Worker, AuditLog, JWT auth
├── store/               ✅ Store, Branch (soft delete, multi-tenant)
├── warehouse/           ❌ Hali boshlanmagan
├── trade/               ❌ Hali boshlanmagan
├── expense/             ❌ Hali boshlanmagan
├── requirements/
│   ├── base.txt
│   └── production.txt   ← gunicorn, whitenoise, dj-database-url
├── requirements.txt     ← -r requirements/production.txt
├── Dockerfile           ← collectstatic BUILD vaqtida
└── railway.toml         ← port 8000 hardcode
```
