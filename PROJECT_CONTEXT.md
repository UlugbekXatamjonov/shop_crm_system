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

## LOYIHA HOLATI (26.02.2026)

| App         | Holat             | Izoh                                                   |
|-------------|-------------------|--------------------------------------------------------|
| `accaunt`   | ✅ Tugallangan    | CustomUser, Worker, AuditLog, JWT auth — 7 ta bug fix tugallandi |
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

## ACCAUNT APP — TO'LIQ TUZILMA

### Modellar

#### WorkerRole (TextChoices)
```python
OWNER   = 'owner',   'Ega'
MANAGER = 'manager', 'Menejer'
SELLER  = 'seller',  'Sotuvchi'
```

#### WorkerStatus (TextChoices)
```python
ACTIVE        = 'active',        'Faol'
TATIL         = 'tatil',         'Tatilda'
ISHDAN_KETGAN = 'ishdan_ketgan', 'Ishdan ketgan'   # max_length=15
```

#### ALL_PERMISSIONS (10 ta kod)
```python
['boshqaruv', 'sotuv', 'dokonlar', 'ombor', 'mahsulotlar',
 'xodimlar', 'savdolar', 'xarajatlar', 'mijozlar', 'sozlamalar']
```

#### ROLE_PERMISSIONS (standart rol permission'lari)
```python
OWNER:   barcha 10 ta permission
MANAGER: boshqaruv, sotuv, dokonlar, ombor, mahsulotlar, xodimlar, savdolar, xarajatlar, mijozlar
SELLER:  sotuv, savdolar, mijozlar, ombor, mahsulotlar
```

#### Worker model maydonlari
| Maydon        | Turi                  | Izoh                                              |
|---------------|-----------------------|---------------------------------------------------|
| `user`        | OneToOneField         | CustomUser bilan bog'liq                          |
| `role`        | CharField(max_length=20) | WorkerRole choices, default=SELLER              |
| `store`       | ForeignKey(Store)     | Do'kon (null=True owner uchun)                    |
| `branch`      | ForeignKey(Branch)    | Filial (null=True)                                |
| `salary`      | DecimalField          | Maoshi UZS da                                     |
| `status`      | CharField(max_length=15) | WorkerStatus choices, default=ACTIVE           |
| `permissions` | JSONField(default=list) | Haqiqiy ruxsatlar ro'yxati, masalan: `["sotuv", "ombor"]` |
| `created_on`  | DateTimeField         | auto_now_add                                      |

**Muhim:** `Worker.permissions` to'g'ridan-to'g'ri ruxsatlar ro'yxati. Hodim yaratilganda
`ROLE_PERMISSIONS[role]` dan avtomatik to'ldiriladi. Owner PATCH orqali istalgan ro'yxat bilan
almashtirishda so'rov formatida `{"permissions": ["sotuv", "ombor"]}` ishlatilinadi.

### Serializerlar

| Serializer                  | Maqsad                                                       |
|-----------------------------|--------------------------------------------------------------|
| `UserRegistrationSerializer`| Ro'yxatdan o'tish (auto Worker(owner) + permissions yaratadi)|
| `UserLoginSerializer`       | Login (username + password)                                  |
| `LogoutSerializer`          | Token blacklist                                              |
| `UserChangePasswordSerializer` | Parol o'zgartirish                                        |
| `ProfileUpdateSerializer`   | PATCH /auth/profil/ — first_name, last_name, phone1, phone2  |
| `WorkerListSerializer`      | Hodimlar ro'yxati (id, full_name, phone1, role, branch, salary, status) |
| `WorkerDetailSerializer`    | Hodim to'liq (+ username, email, phone2, permissions)        |
| `WorkerCreateSerializer`    | Hodim yaratish (user+worker bitta atomic da, permissions auto) |
| `WorkerUpdateSerializer`    | Hodim yangilash — user+worker+permissions bitta PATCH da     |

**WorkerUpdateSerializer PATCH maydonlari:**
```python
# CustomUser maydonlari (source='user.*'):
first_name, last_name, phone1, phone2

# Worker maydonlari:
role, branch, salary, status

# Permission ro'yxati:
permissions  # ["sotuv", "ombor", ...]  — to'liq ro'yxat almashadi
```

### Permission klasslari (`accaunt/permissions.py`)
| Klass            | Shart                                          |
|------------------|------------------------------------------------|
| `IsOwner`        | `worker.role == 'owner'`                       |
| `IsManagerOrAbove` | `worker.role in ('owner', 'manager')`        |
| `CanAccess(code)`| `worker.has_permission(code)`                  |

### Endpointlar

#### Auth (`/api/v1/auth/`)
| Method | URL                        | Ruxsat     | Izoh                          |
|--------|----------------------------|------------|-------------------------------|
| POST   | `/auth/register/`          | AllowAny   | Ro'yxatdan o'tish + JWT token |
| POST   | `/auth/login/`             | AllowAny   | Kirish + profil + JWT token   |
| POST   | `/auth/logout/`            | Auth       | Token blacklist               |
| POST   | `/auth/change-password/`   | Auth       | Parol o'zgartirish            |
| GET    | `/auth/profil/`            | Auth       | O'z profilini ko'rish         |
| PATCH  | `/auth/profil/`            | Auth       | first_name, last_name, phone1, phone2 |
| POST   | `/auth/send-reset-email/`  | AllowAny   | Parol tiklash email           |
| POST   | `/auth/reset-password/{uid}/{token}/` | AllowAny | Yangi parol o'rnatish |

#### Workers (`/api/v1/workers/`)
| Method | URL               | Ruxsat          | Izoh                                                    |
|--------|-------------------|-----------------|---------------------------------------------------------|
| GET    | `/workers/`       | IsManagerOrAbove | Hodimlar ro'yxati (faqat o'z do'koni, status tartibda) |
| POST   | `/workers/`       | IsOwner         | Yangi hodim qo'shish                                    |
| GET    | `/workers/{id}/`  | IsManagerOrAbove | Hodim to'liq ma'lumoti                                 |
| PATCH  | `/workers/{id}/`  | IsOwner         | user+worker+permissions bitta so'rovda                  |
| DELETE | `/workers/{id}/`  | IsOwner         | Soft delete — status='ishdan_ketgan' ga o'tkazadi       |

**http_method_names = ['get', 'post', 'patch', 'delete']**

**Status tartibi (list da):** active → tatil → ishdan_ketgan

**Status o'zgartirish PATCH orqali:**
```json
{"status": "active"}         // faollashtirish
{"status": "tatil"}          // tatilga chiqarish
{"status": "ishdan_ketgan"}  // ishdan chiqarish
```

**Search va filter (GET /workers/):**
```
?search=Ali          → ism/familiya/username/telefon bo'yicha qidirish
?status=active       → holat bo'yicha filter
?role=manager        → rol bo'yicha filter
?branch=3            → filial bo'yicha filter
```

**WorkerCreateSerializer — permissions maydoni:**
```json
// Yuborilmasa → ROLE_PERMISSIONS[role] dan avtomatik
// Yuborilsa → berilgan ro'yxat ishlatiladi
{"permissions": ["sotuv", "ombor", "xarajatlar"]}
```

**Branch validatsiyasi:** Worker qo'shganda/yangilaganda faqat owner do'konining filiallari qabul qilinadi.

**Telefon validatsiyasi:** `+998XXXXXXXXX` format majburiy (WorkerCreate, WorkerUpdate, ProfileUpdate).

**Validation xatolari:** Barcha majburiy maydon, format, uzunlik xatolari o'zbek tilida.

### Migratsiyalar
| Migration | Izoh                                                           |
|-----------|----------------------------------------------------------------|
| 0001      | Dastlabki CustomUser va Worker modellari                       |
| 0002      | role_permissions olib tashlandi, boshqa o'zgarishlar           |
| 0003      | branch verbose_name                                            |
| 0004      | WorkerRole (sotuvchi→seller), WorkerStatus (deactive→tatil/ishdan_ketgan), max_length=15 + data migration |
| 0005      | Worker.extra_permissions → Worker.permissions (flat list) + data migration |

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
- `list/retrieve` → `IsAuthenticated + CanAccess('mahsulotlar')` yoki `CanAccess('ombor')`
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
- Claude worktree da ishlaydi: `.claude/worktrees/elegant-bhaskara/`
- **Har o'zgarishdan keyin:** `git commit` → DARHOL `git cherry-pick` main branchga
- `__pycache__`, `db.sqlite3`, `.claude/settings.local.json` ni HECH QACHON commit qilma

### Virtual env
```bash
# Python executable:
D:/projects/shop_crm_system/myenv/Scripts/python.exe

# Django management commands:
"D:/projects/shop_crm_system/myenv/Scripts/python.exe" manage.py <command>
```

### Migration yaratish
```bash
python manage.py makemigrations appname --settings=config.settings.local
python manage.py migrate appname --settings=config.settings.local
```

### Git log (so'nggi commitlar, 26.02.2026)
```
9556466  fix(accaunt): worker API 7 ta xatolik tuzatildi
6ec2689  refactor(accaunt): replace extra_permissions with direct permissions field
26cfec2  refactor(accaunt): worker/profil tahrirlash huquqlari aniqlantirildi
7ac4f5d  refactor(accaunt): activate/deactivate o'chirildi, PATCH status ga ko'chirildi
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
│   ├── models.py         ← CustomUser, Worker(permissions JSONField), AuditLog
│   ├── views.py          ← Register, Login, Logout, ProfileView, WorkerViewSet
│   ├── serializers.py    ← WorkerUpdateSerializer (user+worker+permissions bitta PATCH)
│   ├── permissions.py    ← IsOwner, IsManagerOrAbove, CanAccess
│   ├── urls.py           ← /api/v1/auth/
│   ├── api_urls.py       ← /api/v1/workers/
│   └── migrations/
│       ├── 0004_...      ← role/status o'zgarishlar + data migration
│       └── 0005_...      ← extra_permissions → permissions + data migration
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
