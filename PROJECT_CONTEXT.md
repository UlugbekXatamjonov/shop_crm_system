# CLAUDE UCHUN ESLATMA — Yangi chatda bu faylni o'qi va davom et

## Sen kim bilan ishlayapsan
Foydalanuvchi: Ulugbek (Django dasturchisi)
Loyiha: `D:\projects\shop_crm_system` (GitHub: `UlugbekXatamjonov/shop_crm_system`, `main` branch)

## Loyiha nima
Django 5.2 REST API — Shop CRM tizimi (backend only).
Frontend: `https://shop-crm-front.vercel.app/`
Stack: DRF + SimpleJWT + Celery + Redis + PostgreSQL + Gunicorn.
Python 3.12. Dockerfile bor. docker-compose bor (local uchun).
Settings: `config/settings/base.py` → `local.py` (SQLite) / `production.py` (PostgreSQL+Redis).

---

## LOYIHA HOLATI (24.02.2026)

| App         | Holat             | Izoh                                                   |
|-------------|-------------------|--------------------------------------------------------|
| `accaunt`   | ✅ Tugallangan    | CustomUser, Worker, AuditLog, JWT auth                 |
| `store`     | ✅ Tugallangan    | Store, Branch CRUD (soft delete, multi-tenant)         |
| `warehouse` | ✅ Tugallangan    | Category, Product, Stock, StockMovement (kirim/chiqim) |
| `trade`     | ❌ Boshlanmagan  | Navbatda                                               |
| `expense`   | ❌ Boshlanmagan  | Navbatda                                               |

---

## STANDART RESPONSE PATTERN (BARCHA APPLICATION)

Barcha write operatsiyalarda shu pattern ishlatiladi:

| Metod      | Status | Javob formati                       |
|------------|--------|-------------------------------------|
| `create`   | 201    | `{'message': '...', 'data': {...}}` |
| `update`   | 200    | `{'message': '...', 'data': {...}}` |
| `destroy`  | 200    | `{'message': '...'}`                |
| `list`     | 200    | faqat `[...]` (message yo'q)        |
| `retrieve` | 200    | faqat `{...}` (message yo'q)        |

---

## WAREHOUSE APP — TUZILMA (to'liq)

### Modellar
| Model           | Maydonlar                                                                 |
|-----------------|---------------------------------------------------------------------------|
| `Category`      | name, description, store(FK), status, created_on                          |
| `Product`       | name, category(FK), unit, purchase_price, sale_price, barcode, store(FK), status, created_on |
| `Stock`         | product(FK), branch(FK), quantity, updated_on — unique_together(product, branch) |
| `StockMovement` | product(FK), branch(FK), movement_type(in/out), quantity, note, worker(FK), created_on |

### Choices
- `ProductUnit`: dona, kg, g, litr, metr, m2, yashik, qop
- `ProductStatus`: active, inactive
- `MovementType`: in (Kirim), out (Chiqim)

### Endpointlar
```
GET/POST   /api/v1/warehouse/categories/   + PATCH/DELETE /{id}/
GET/POST   /api/v1/warehouse/products/     + PATCH/DELETE /{id}/
GET/POST   /api/v1/warehouse/stocks/       + PATCH/DELETE /{id}/
GET/POST   /api/v1/warehouse/movements/    + GET          /{id}/   (immutable)
```

### Ruxsatlar
- `list/retrieve` → `IsAuthenticated + CanAccess('mahsulotlar')` yoki `CanAccess('sklad')`
- `create/update/destroy` → `IsAuthenticated + IsManagerOrAbove`
- `StockMovement` → faqat `GET` va `POST` (http_method_names = ['get', 'post'])

### Muhim logika
- **StockMovement POST** → `Stock.quantity` avtomatik yangilanadi (`get_or_create`)
- **Chiqim (`out`)** uchun qoldiq serializer'da tekshiriladi (yetarli bo'lmasa → 400)
- **Soft delete**: Category, Product (`status='inactive'`)
- **Stock** → hard delete (o'chirish mumkin)
- **Multi-tenant**: `get_queryset()` — `worker.store` bo'yicha filtrlash
- **AuditLog**: barcha write operatsiyalarda yoziladi

---

## CORS SOZLAMALARI

### `base.py` (development + barcha muhit)
```python
CORS_ORIGIN_WHITELIST = (
    'http://localhost:5173',
    'http://localhost:8080',
    'http://localhost:3000',
    'https://shop-crm-front.vercel.app',   # ← Production frontend
)
```

### `production.py` (Railway)
```python
CORS_ORIGIN_WHITELIST = tuple([
    'https://shop-crm-front.vercel.app',   # hardcode
    *_extra_origins,                        # + CORS_ALLOWED_ORIGINS env (ixtiyoriy)
])
```

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
**Frontend URL:** https://shop-crm-front.vercel.app/

---

## KEYINGI ISHLAR (navbat)

### `trade` app — to'liq qurish kerak
- `Sale` — sotuv (Branch, Worker, vaqt, jami summa)
- `SaleItem` — sotuv tarkibi (Sale, Product, miqdor, narx)

### `expense` app — to'liq qurish kerak
- `ExpenseCategory` — xarajat kategoriyasi
- `Expense` — xarajat (Branch, Worker, miqdor, izoh, sana)

---

## MUHIM ESLATMALAR

### Worktree pattern (MAJBURIY)
- Claude worktree da ishlaydi: `.claude/worktrees/priceless-brown/`
- Har o'zgarishdan keyin: `git add` → `git commit`
- `__pycache__` va `db.sqlite3` ni HECH QACHON commit qilma

### Virtual env
```bash
source /d/projects/shop_crm_system/myenv/Scripts/activate
```

### Migration yaratish
```bash
python manage.py makemigrations appname --settings=config.settings.local
python manage.py migrate appname --settings=config.settings.local
```

### Git log (so'nggi commitlar)
```
e1e0910  feat(cors): Vercel frontend URL qo'shildi
a4e59f1  feat(warehouse): warehouse app to'liq qurildi
acc1d9f  feat(accaunt): WorkerViewSet update/destroy metodlari va message+data pattern
19125a9  feat(store): create/update javoblariga message+data qo'shildi
f6bf1f3  fix(railway): PORT mismatch tuzatildi
```

---

## LOYIHA TUZILMASI

```
shop_crm_system/
├── config/
│   ├── __init__.py       ← Celery import
│   ├── celery.py         ← Celery konfiguratsiya
│   ├── middleware.py     ← HealthCheckMiddleware
│   ├── settings/
│   │   ├── base.py       ← Umumiy sozlamalar (CORS, JWT, DRF, Celery)
│   │   ├── local.py      ← Development (SQLite)
│   │   └── production.py ← Production (PostgreSQL+Redis+WhiteNoise+CORS)
│   ├── urls.py           ← /health/, /api/v1/, /swagger/
│   └── wsgi.py
├── accaunt/              ✅ CustomUser, Worker, AuditLog, JWT auth
│   ├── models.py         ← CustomUser, Worker, AuditLog + permissions
│   ├── views.py          ← Register, Login, Logout, Profile, WorkerViewSet
│   ├── serializers.py
│   ├── permissions.py    ← IsOwner, IsManagerOrAbove, IsSotuvchiOrAbove, CanAccess
│   ├── urls.py           ← /api/v1/auth/
│   └── api_urls.py       ← /api/v1/workers/
├── store/                ✅ Store, Branch (soft delete, multi-tenant)
│   ├── models.py         ← Store, Branch, StoreStatus
│   ├── views.py          ← StoreViewSet, BranchViewSet
│   ├── serializers.py
│   └── api_urls.py       ← /api/v1/stores/, /api/v1/branches/
├── warehouse/            ✅ Category, Product, Stock, StockMovement
│   ├── models.py         ← Category, Product, Stock, StockMovement
│   ├── views.py          ← CategoryViewSet, ProductViewSet, StockViewSet, StockMovementViewSet
│   ├── serializers.py    ← 14 ta serializer
│   ├── api_urls.py       ← /api/v1/warehouse/
│   └── migrations/0001_initial.py
├── trade/                ❌ Hali boshlanmagan
├── expense/              ❌ Hali boshlanmagan
├── requirements/
│   ├── base.txt
│   └── production.txt    ← gunicorn, whitenoise, dj-database-url
├── requirements.txt      ← -r requirements/production.txt
├── Dockerfile            ← collectstatic BUILD vaqtida
└── railway.toml          ← port 8000 hardcode
```
