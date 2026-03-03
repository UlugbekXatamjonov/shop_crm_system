# CLAUDE UCHUN ESLATMA — Yangi chatda bu faylni o'qi va davom et

## ⚠️ MUHIM: 3 TA QOIDA (HECH QACHON UNUTMA)

### QOIDA 1 — StoreSettings SIGNAL
Store yaratilganda AVTOMATIK default StoreSettings yaratilishi SHART:
```python
@receiver(post_save, sender=Store)
def create_store_settings(sender, instance, created, **kwargs):
    if created:
        StoreSettings.objects.create(store=instance)
```
**Sabab:** Hech qachon "sozlamalar topilmadi" xatosi bo'lmasligi kerak.

### QOIDA 2 — select_related BILAN TORTISH
Settings ga murojaat qilganda DOIM select_related:
```python
worker.store  # allaqachon worker bilan keladigan
store.settings  # + 1 JOIN, undan ko'p emas
# Yoki ViewSet da: queryset.select_related('store__settings')
```
**Sabab:** N+1 query muammosi bo'lmasin.

### QOIDA 3 — Redis KESH (5 daqiqa)
```python
def get_store_settings(store_id):
    key = f'store_settings_{store_id}'
    settings = cache.get(key)
    if not settings:
        settings = StoreSettings.objects.get(store_id=store_id)
        cache.set(key, settings, timeout=300)
    return settings
# Sozlamalar o'zgarganda: cache.delete(f'store_settings_{store_id}')
```
**Sabab:** 200 do'kon × tez-tez bir xil so'rov → DB ga har gal bormasin.

---

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

## LOYIHA HOLATI (03.03.2026)

| App         | Holat             | Izoh                                                   |
|-------------|-------------------|--------------------------------------------------------|
| `accaunt`   | ✅ Tugallangan    | CustomUser, Worker, AuditLog, JWT auth — password reset, WorkerList/Detail da store+branch |
| `store`     | ✅ Tugallangan    | Store, Branch CRUD (soft delete, multi-tenant, workers in detail, Uzbek errors) |
| `warehouse` | ✅ Tugallangan    | Category, **SubCategory**, Product(+image, +barcode EAN-13, +subcategory, +price_currency), **Currency**, **ExchangeRate**, Stock, StockMovement (race condition tuzatildi) — BOSQICH 1 ✅ |
| `trade`     | ✅ Tugallangan   | BOSQICH 4 ✅ — CustomerGroup, Customer (soft delete), Sale (@transaction.atomic, 13-qadam), SaleItem, cancel action, _build_report() to'ldirildi |
| `expense`   | ❌ Boshlanmagan  | BOSQICH 6 — ExpenseCategory, Expense                   |
| `StoreSettings` | ✅ Tugallangan  | BOSQICH 2 ✅ — 10 guruh, 30+ maydon, signal+Redis kesh |
| `Smena`     | ✅ Tugallangan   | BOSQICH 3 ✅ — SmenaStatus+Smena model, SmenaViewSet (open/close/x-report), migration 0005 |
| `SaleReturn` | ❌ Boshlanmagan | BOSQICH 5 — trade app da                               |
| `WastageRecord` | ❌ Boshlanmagan | BOSQICH 7 — warehouse app da                        |
| `StockAudit` | ❌ Boshlanmagan | BOSQICH 8 — warehouse app da                           |
| `WorkerKPI` | ❌ Boshlanmagan  | BOSQICH 9 — accaunt app da                             |
| `Z/X-report` | ❌ Boshlanmagan | BOSQICH 10 — trade app da                              |
| `Telegram bot` | ❌ Boshlanmagan | BOSQICH 11 — config/telegram.py yoki alohida          |
| `PriceList` | ❌ Boshlanmagan  | BOSQICH 12 — trade app da                              |
| `Supplier`  | ❌ Boshlanmagan  | BOSQICH 13 — v2, keyingi versiyada                     |
| `OFD`       | ❌ Boshlanmagan  | BOSQICH 14 — v2, keyingi versiyada (Uzbekistonda MAJBURIY 2026) |
| `Offline sync` | ❌ Boshlanmagan | BOSQICH 18 — idempotency + sync queue                |

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
| `UserChangePasswordSerializer`        | POST /auth/change-password/ — current_password, password, password2 (save update_fields=['password']) |
| `SendPasswordResetEmailSerializer`    | POST /auth/send-reset-email/ — email bo'yicha tiklash havolasi yuboradi |
| `UserPasswordResetSerializer`         | POST /auth/reset-password/<uid>/<token>/ — yangi parol o'rnatadi |
| `ProfileUpdateSerializer`   | PATCH /auth/profil/ — first_name, last_name, phone1, phone2  |
| `WorkerListSerializer`      | Hodimlar ro'yxati (id, full_name, phone1, role, branch_id, branch_name, store_id, store_name, salary, status) — null safe SerializerMethodField |
| `WorkerDetailSerializer`    | Hodim to'liq (+ username, email, phone2, branch_id, branch_name, store_id, store_name, permissions) — null safe SerializerMethodField |
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
| Klass              | Shart                                          |
|--------------------|------------------------------------------------|
| `IsOwner`          | `worker.role == WorkerRole.OWNER`              |
| `IsManagerOrAbove` | `worker.role in {WorkerRole.OWNER, WorkerRole.MANAGER}` |
| `IsSotuvchiOrAbove`| `worker.status == WorkerStatus.ACTIVE`         |
| `CanAccess(code)`  | `worker.has_permission(code)`                  |

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

### admin.py — tuzatilgan (26.02.2026)
- `WorkerAdmin` da `extra_permissions` → `permissions` ga o'zgartirildi (migration 0005 bilan mos)
- `get_computed_permissions` method olib tashlandi
- `permissions` field JSONField sifatida ko'rsatiladi, format: `["sotuv", "ombor"]`

---

## STORE APP — TUZILMA (to'liq, 27.02.2026)

### Modellar
| Model    | Maydonlar                                              | Constraint                        |
|----------|--------------------------------------------------------|-----------------------------------|
| `Store`  | name, address, phone, status, created_on               | Yo'q (har owner o'z nomini tanlaydi) |
| `Branch` | store(FK), name, address, phone, status, created_on    | `unique_together = [('store','name')]` |

- `StoreStatus`: `active`, `inactive`
- **Soft delete**: `status='inactive'` ga o'tkaziladi (o'chirilmaydi)

### Serializer maydonlari

| Serializer              | Maydonlar                                               |
|-------------------------|---------------------------------------------------------|
| `StoreListSerializer`   | id, name, phone, status, status_display, branch_count   |
| `StoreDetailSerializer` | id, name, address, phone, status, status_display, created_on, **branches**, **workers** |
| `StoreCreateSerializer` | name, address, phone                                    |
| `StoreUpdateSerializer` | name, address, phone, **status**                        |
| `BranchListSerializer`  | id, name, store_name, phone, status, status_display     |
| `BranchDetailSerializer`| id, name, address, phone, store_id, store_name, status, status_display, created_on, **workers** |
| `BranchCreateSerializer`| name, address, phone                                    |
| `BranchUpdateSerializer`| name, address, phone, **status**                        |

**workers maydoni** (faqat detail da): `[{"id": 1, "full_name": "Ali Valiyev"}, ...]`
**branches maydoni** (faqat StoreDetail da): faqat `active` filiallar, `BranchListSerializer` orqali

### Migratsiyalar
| Migration | Izoh                                                |
|-----------|-----------------------------------------------------|
| 0001      | Store, Branch dastlabki modellar                    |
| 0002      | ...                                                 |
| 0003      | Branch unique_together [('store', 'name')] qo'shildi |

### Endpointlar
| Method | URL                   | Ruxsat                        | Izoh                   |
|--------|-----------------------|-------------------------------|------------------------|
| GET    | `/api/v1/stores/`     | IsAuthenticated + CanAccess('dokonlar') | Ro'yxat (branch_count) |
| POST   | `/api/v1/stores/`     | IsOwner                       | Yaratish               |
| GET    | `/api/v1/stores/{id}/`| IsAuthenticated + CanAccess('dokonlar') | Detail (branches+workers) |
| PATCH  | `/api/v1/stores/{id}/`| IsOwner                       | Yangilash (+ status)   |
| DELETE | `/api/v1/stores/{id}/`| IsOwner                       | Soft delete            |
| GET    | `/api/v1/branches/`   | IsAuthenticated               | Ro'yxat                |
| POST   | `/api/v1/branches/`   | IsOwner                       | Yaratish               |
| GET    | `/api/v1/branches/{id}/`| IsAuthenticated             | Detail (workers)       |
| PATCH  | `/api/v1/branches/{id}/`| IsOwner                     | Yangilash (+ status)   |
| DELETE | `/api/v1/branches/{id}/`| IsOwner                     | Soft delete            |

---

## WAREHOUSE APP — TUZILMA (to'liq, 03.03.2026 yangilandi)

### Modellar (haqiqiy)
| Model           | Maydonlar                                                                 | Constraint |
|-----------------|---------------------------------------------------------------------------|------------|
| `Category`      | name, description, store(FK), status, created_on                          | `unique_together = [('store','name')]` |
| `SubCategory`   | name, category(FK), store(FK), status, created_on                         | `unique_together = [('store','name')]` |
| `Currency`      | code, name, symbol, is_base — **store YO'Q, global**                      | `unique: code` |
| `ExchangeRate`  | currency(FK), rate, date, source, created_on — **store YO'Q, global**     | `unique_together = [('currency','date')]` |
| `Product`       | name, category(FK), subcategory(FK,null), unit, purchase_price, sale_price, price_currency(FK,null), barcode(null), image(null), store(FK), status, created_on | `unique_together = [('store','name')]` |
| `Stock`         | product(FK), branch(FK), quantity, updated_on                             | `unique_together = [('product','branch')]` |
| `StockMovement` | product(FK), branch(FK), movement_type, quantity, note, worker(FK,null), created_on | — (immutable log) |

⚠️ **Muhim:** `Warehouse` modeli **mavjud emas**. `Stock` faqat `branch` ga bog'liq.
⚠️ `Currency` va `ExchangeRate` da `store` maydoni **yo'q** — ular global (barcha do'konlar uchun umumiy).

### Choices
- `ProductUnit`: dona, kg, g, litr, metr, m2, yashik, qop, quti
- `ProductStatus`: active, inactive
- `MovementType`: in (Kirim), out (Chiqim)

### Migratsiyalar (to'g'ri zanjir!)
| Migration | Fayl nomi                          | Izoh                                                    |
|-----------|------------------------------------|---------------------------------------------------------|
| 0001      | 0001_initial.py                    | Dastlabki modellar                                      |
| 0002      | 0002_alter_product_unique_together | Product unique_together                                 |
| 0003      | 0003_expand_warehouse_models.py    | Kengaytirilgan modellar                                 |
| 0004 (a)  | 0004_product_image.py              | Product.image ImageField (0003 ga bog'liq)              |
| 0004 (b)  | 0004_subcategory.py                | SubCategory + Product.subcategory (**0004_product_image** ga bog'liq ✅) |
| 0005      | 0005_currency_exchangerate.py      | Currency + ExchangeRate + seed data (0004_subcategory ga bog'liq) |

⚠️ **Muhim:** `0004_subcategory` → `('warehouse', '0004_product_image')` ga bog'liq (0003_product_image emas!)
`trade.0001_initial` → `('warehouse', '0005_currency_exchangerate')` ga bog'liq ✅

### Endpointlar
```
GET/POST   /api/v1/warehouse/categories/    + PATCH/DELETE /{id}/
GET/POST   /api/v1/warehouse/subcategories/ + PATCH/DELETE /{id}/
GET/POST   /api/v1/warehouse/currencies/    + PATCH        /{id}/   (faqat list/retrieve/update)
GET/POST   /api/v1/warehouse/exchange-rates/+ GET          /{id}/   (faqat list/retrieve/create)
GET/POST   /api/v1/warehouse/products/      + PATCH/DELETE /{id}/
GET/POST   /api/v1/warehouse/stocks/        + PATCH/DELETE /{id}/
GET/POST   /api/v1/warehouse/movements/     + GET          /{id}/   (immutable)
```

### Ruxsatlar
- `list/retrieve` → `IsAuthenticated + CanAccess('mahsulotlar')` yoki `CanAccess('ombor')`
- `create/update/destroy` → `IsAuthenticated + IsManagerOrAbove`
- `StockMovement` → faqat `GET` va `POST` (http_method_names = ['get', 'post'])

### Muhim logika
- **StockMovement POST** → `Stock.quantity` avtomatik yangilanadi (`@transaction.atomic` + `select_for_update()` + `F()` expression — race condition yo'q)
- **Chiqim (`out`)** uchun qoldiq serializer'da tekshiriladi (yetarli bo'lmasa → 400)
- **Soft delete**: Category, SubCategory, Product (`status='inactive'`)
- **Stock** → hard delete (o'chirish mumkin)
- **Multi-tenant**: `get_queryset()` — `worker.store` bo'yicha filtrlash
- **AuditLog**: barcha write operatsiyalarda yoziladi

---

## CONFIG — MUHIM SOZLAMALAR (03.03.2026)

### `config/settings/base.py` — FRONTEND_URL
```python
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'https://shop-crm-front.vercel.app')
# Parol tiklash havolasi uchun ishlatiladi
# SendPasswordResetEmailSerializer: f'{settings.FRONTEND_URL}/reset-password/{uid}/{token}'
```
**Railway Variables ga qo'shish kerak:** `FRONTEND_URL=https://shop-crm-front.vercel.app`

### `config/settings/base.py` — REST_FRAMEWORK
```python
REST_FRAMEWORK = {
    ...
    'DATETIME_FORMAT': '%Y-%m-%d | %H:%M',              # "2026-02-27 | 14:30" formatida
    'EXCEPTION_HANDLER': 'config.exceptions.custom_exception_handler',
}
```

### `config/exceptions.py` — O'zbek tilidagi xato xabarlari
```python
UZBEK_ERROR_MESSAGES = {
    400: "So'rov ma'lumotlari noto'g'ri.",
    401: "Tizimga kirish talab etiladi. Iltimos, avval login qiling.",
    403: "Bu amalni bajarishga ruxsatingiz yo'q.",
    404: "So'ralgan ma'lumot topilmadi.",
    405: "Bu so'rov turi ({method}) qo'llab-quvvatlanmaydi.",
    429: "So'rovlar soni limitdan oshdi. Keyinroq urinib ko'ring.",
    500: "Server xatosi yuz berdi. Iltimos, keyinroq urinib ko'ring.",
}
# Faqat {'detail': '...'} ko'rinishdagi xatolarda ishlaydi.
# Field-level (validation) xatolarga tegmaydi.
```

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

CORS_ALLOW_HEADERS = [
    'accept', 'accept-encoding', 'authorization',
    'content-type', 'dnt', 'origin', 'user-agent',
    'x-csrftoken', 'x-requested-with',
    'x-idempotency-key',  # ← Offline rejim uchun (BOSQICH 18) — 03.03.2026 qo'shildi
]
```

### `production.py` (Railway)
```python
CORS_ORIGIN_WHITELIST = tuple([
    'https://shop-crm-front.vercel.app',   # hardcode
    *_extra_origins,                        # + CORS_ALLOWED_ORIGINS env (ixtiyoriy)
])
```

---

## LOCAL DEV ENVIRONMENT (03.03.2026 sozlandi)

```
Virtual env:  D:\projects\my_projects\shop_crm_system\myenv\
Python:       myenv\Scripts\python.exe  (Django 5.2.11, Celery 5.6.2)
Settings:     config.settings.local  (SQLite, DEBUG=True)
```

**`.claude/launch.json` — 3 ta server:**
```json
{
  "name": "Django Dev Server",
  "runtimeExecutable": "D:\\...\\myenv\\Scripts\\python.exe",
  "runtimeArgs": ["manage.py", "runserver", "8000", "--settings=config.settings.local"],
  "port": 8000
}
```
Server: `http://127.0.0.1:8000/`
Swagger: `http://127.0.0.1:8000/swagger/`

**Foydali buyruqlar:**
```bash
# Migrate (local)
myenv\Scripts\python.exe manage.py migrate --settings=config.settings.local

# Check (xatolarni oldindan tekshirish)
myenv\Scripts\python.exe manage.py check --settings=config.settings.local

# showmigrations
myenv\Scripts\python.exe manage.py showmigrations --settings=config.settings.local
```

---

## RAILWAY DEPLOY — TUZATILGAN MUAMMOLAR (03.03.2026)

| # | Xato | Sabab | Tuzatish |
|---|------|-------|----------|
| 1 | `ImportError: cannot import name 'Warehouse'` | `warehouse/admin.py` da mavjud bo'lmagan `Warehouse` modeli import qilingan | `Warehouse` o'chirildi, to'g'ri modellar yozildi |
| 2 | `admin.E108/E116` — `store`, `created_on` topilmadi | `Currency` va `ExchangeRate` da `store` maydoni yo'q | Admin `list_display/list_filter` haqiqiy maydonlar bilan to'g'rilanaldi |
| 3 | `NodeNotFoundError: '0003_product_image'` | `0004_subcategory.py` da noto'g'ri dependency (`0003_product_image` degan fayl yo'q) | `('warehouse', '0003_product_image')` → `('warehouse', '0004_product_image')` |

**⚠️ Deploy oldi nazorat (har safar):**
```bash
python manage.py check --settings=config.settings.local
# "System check identified no issues" bo'lishi SHART
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

## TO'LIQ LOYIHA REJASI — 20 BOSQICH (ASLO UNUTMA)

---

### BOSQICH 0 — Tayyorlov (Infratuzilma) ✅ BAJARILDI
| # | Vazifa | Holat |
|---|--------|-------|
| 0.1 | `MEDIA_URL = '/media/'` va `MEDIA_ROOT = BASE_DIR / 'media'` — `base.py` da | ✅ Allaqachon bor |
| 0.2 | `urls.py` da `if settings.DEBUG: urlpatterns += static(MEDIA_URL, ...)` | ✅ Allaqachon bor |
| 0.3 | `CORS_ALLOW_HEADERS` ga `'x-idempotency-key'` qo'shildi (offline rejim uchun) | ✅ 03.03.2026 qo'shildi |
| 0.4 | `CORS_ALLOW_HEADERS` da barcha kerakli headerlar to'liq | ✅ Allaqachon to'g'ri |

**Natija:** Mahsulot rasmlari, xarajat cheklari, barcha media fayllar ishlaydi. Offline sync header'i qabul qilinadi.

---

### BOSQICH 1 — warehouse ni to'ldirish ✅ BAJARILDI (03.03.2026)
| # | Vazifa | Holat |
|---|--------|-------|
| 1.1 | SubCategory (Category → SubCategory → Product, ixtiyoriy) | ✅ Bajarildi |
| 1.2 | Barcode auto-generate (EAN-13, prefix 2XXXX GS1 in-store, python-barcode) | ✅ Bajarildi |
| 1.3 | Multi-valyuta: Currency model + ExchangeRate + price_currency on Product | ✅ Bajarildi |
| 1.4 | Celery task: kurs kunlik avtomatik yangilanishi (O'zbekiston CBU API) | ✅ Bajarildi |

**Barcode format:** `20{store_id:05d}{seq:05d}{check}` — 13 raqam EAN-13 (GS1 in-store prefix 20, hech qachon real GS1 bilan to'qnashmaydi).
**Currency seed (migration 0005):** UZS (asosiy), USD, EUR, RUB, CNY.
**Celery schedule:** `CELERY_BEAT_SCHEDULE` — `update_exchange_rates` har kuni soat 09:00 da (`crontab(hour=9, minute=0)`).

**Yangi fayllar:**
- `warehouse/utils.py` — `generate_unique_barcode()`, `get_barcode_image()`, `get_barcode_svg()`, `get_today_rate()`
- `warehouse/tasks.py` — `update_exchange_rates` Celery task (CBU API, retry 3×5min)
- `warehouse/migrations/0004_subcategory.py` — SubCategory + Product.subcategory
- `warehouse/migrations/0005_currency_exchangerate.py` — Currency + ExchangeRate + Product.price_currency + seed

---

### BOSQICH 2 — StoreSettings (Sozlamalar) ✅ BAJARILDI (03.03.2026)
**⚠️ QOIDA 1, 2, 3 SHU YERDA QO'LLANILADI!**

```python
# StoreSettings modeli (OneToOneField → Store, store app da yashaydi)
# ============================================================
# GURUH 1 — Modul on/off flaglari (IXTIYORIY, default=False/True)
# ============================================================
subcategory_enabled   = BooleanField(default=False)  # SubCategory (1.1) — kichik do'konlarda off
sale_return_enabled   = BooleanField(default=True)   # SaleReturn (B5)   — aksariyat do'konlarda on
wastage_enabled       = BooleanField(default=True)   # WastageRecord (B7) — on, lekin ishlatmaslik mumkin
stock_audit_enabled   = BooleanField(default=True)   # StockAudit (B8)   — on
kpi_enabled           = BooleanField(default=False)  # WorkerKPI (B9)    — faqat xohlagan owner yoqadi
price_list_enabled    = BooleanField(default=False)  # PriceList (B12)   — faqat ulgurji/retail farq uchun

# ============================================================
# GURUH 2 — Valyuta sozlamalari
# ============================================================
default_currency      = CharField(max_length=3, default='UZS')  # UZS | USD | RUB
show_usd_price        = BooleanField(default=False)  # USD narxini ko'rsatish
show_rub_price        = BooleanField(default=False)  # RUB narxini ko'rsatish

# ============================================================
# GURUH 3 — To'lov sozlamalari
# ============================================================
allow_cash            = BooleanField(default=True)   # Naqd to'lov
allow_card            = BooleanField(default=True)   # Karta to'lov
allow_debt            = BooleanField(default=False)  # Nasiya (qarz)

# ============================================================
# GURUH 4 — Chegirma sozlamalari
# ============================================================
allow_discount        = BooleanField(default=True)   # Chegirma berish ruxsati
max_discount_percent  = DecimalField(default=0)      # Maksimal chegirma foizi (0 = cheksiz)

# ============================================================
# GURUH 5 — Chek sozlamalari
# ============================================================
receipt_header        = TextField(blank=True)        # Chek yuqori matni
receipt_footer        = TextField(blank=True)        # Chek pastki matni
show_store_logo       = BooleanField(default=False)  # Chekda do'kon logosi
show_worker_name      = BooleanField(default=True)   # Chekda kassir ismi

# ============================================================
# GURUH 6 — Ombor sozlamalari
# ============================================================
low_stock_enabled     = BooleanField(default=True)   # Kam qoldiq ogohlantirish
low_stock_threshold   = IntegerField(default=5)      # Ogohlantirish chegarasi (dona)

# ============================================================
# GURUH 7 — Smena sozlamalari
# ============================================================
shift_enabled         = BooleanField(default=False)  # Smena tizimi
shifts_per_day        = IntegerField(default=1)      # Kunlik smena soni (1/2/3)
require_cash_count    = BooleanField(default=False)  # Smena ochish/yopishda naqd hisoblash majburiy

# ============================================================
# GURUH 8 — Telegram sozlamalari
# ============================================================
telegram_enabled      = BooleanField(default=False)  # Telegram bildirishnomalar
telegram_chat_id      = CharField(max_length=50, null=True, blank=True)

# ============================================================
# GURUH 9 — Soliq sozlamalari (OFD v2 uchun)
# ============================================================
tax_enabled           = BooleanField(default=False)  # QQS (OFD v2 da majburiy)
tax_percent           = DecimalField(default=12)     # QQS foizi (O'zbekistonda 12%)
ofd_enabled           = BooleanField(default=False)  # OFD integratsiya (v2)
ofd_token             = CharField(max_length=255, null=True, blank=True)
ofd_device_id         = CharField(max_length=100, null=True, blank=True)

# ============================================================
# GURUH 10 — Yetkazib beruvchi sozlamalari (v2)
# ============================================================
supplier_credit_enabled = BooleanField(default=False)  # Yetkazib beruvchi qarz hisobi
```

**Barcha flaglar uchun ViewSet tekshirish pattern:**
```python
def perform_create(self, serializer):
    settings = get_store_settings(self.request.user.worker.store_id)  # QOIDA 3 (Redis kesh)
    if not settings.sale_return_enabled:
        raise PermissionDenied("Qaytarish bu do'konda o'chirilgan.")
    serializer.save(worker=self.request.user.worker)
```

**Signal:** Store yaratilganda `StoreSettings` AVTOMATIK yaratiladi (QOIDA 1).

**Yangi fayllar:**
- `store/signals.py` — `create_store_settings` post_save signal (QOIDA 1)
- `store/apps.py` — `ready()` → `import store.signals`
- `config/cache_utils.py` — `get_store_settings()` + `invalidate_store_settings()` (QOIDA 3)
- `store/migrations/0004_storesettings.py` — StoreSettings jadval yaratish

**Endpointlar:**
- `GET  /api/v1/settings/`      — o'z do'koni sozlamalarini ko'rish (`CanAccess('sozlamalar')`)
- `PATCH /api/v1/settings/{id}/` — sozlamalarni yangilash (`IsOwner`)

---

### BOSQICH 3 — Smena (Shift) ✅ BAJARILDI (03.03.2026)
```
Smena model (store app da yashaydi):
  branch(FK), store(FK)
  worker_open(FK→Worker), worker_close(FK→Worker, null)
  start_time(auto_now_add), end_time(null)
  status: open | closed   (SmenaStatus TextChoices)
  cash_start(DecimalField, default=0), cash_end(null)
  note(blank)
  ordering: ['-start_time']
```

**Endpointlar:**
- `GET  /api/v1/shifts/`                 — ro'yxat (?status=open|closed, ?branch=id)
- `POST /api/v1/shifts/`                 — smena ochish
- `GET  /api/v1/shifts/{id}/`            — to'liq ma'lumot
- `PATCH /api/v1/shifts/{id}/close/`     — Z-report + yopish
- `GET  /api/v1/shifts/{id}/x-report/`  — X-report (yopilmaydi)

**Biznes qoidalari:**
- shift_enabled=False → smena ochib bo'lmaydi (403)
- Bir filialda bir vaqtda faqat bitta OPEN smena (400)
- require_cash_count=True → cash_start/cash_end majburiy
- Yopilgan smenani qayta yopib bo'lmaydi (400)

**Keyingi bosqichlarda to'ldiriladi:**
- BOSQICH 4 (Sale): Sale.smena(FK,null) + X/Z report da savdolar
- BOSQICH 6 (Expense): Expense.smena(FK,null) + X/Z report da xarajatlar

**Yangi fayllar:**
- `store/migrations/0005_smena.py` — Smena jadval migratsiyasi

**Yangilangan fayllar:**
- `store/models.py` — SmenaStatus + Smena model qo'shildi
- `store/serializers.py` — SmenaListSerializer, SmenaDetailSerializer, SmenaOpenSerializer, SmenaCloseSerializer
- `store/views.py` — SmenaViewSet (create, close action, x_report action, _build_report)
- `store/api_urls.py` — /shifts/ router qo'shildi

---

### BOSQICH 4 — trade app (Savdolar + Mijozlar) ✅ BAJARILDI (03.03.2026)

**Modellar:**
```
CustomerGroup: name, store(FK), discount(%), created_on
               unique_together = [('store', 'name')]

Customer:      name, phone, address, debt_balance, group(FK,null),
               store(FK), status(active|inactive), created_on
               → Soft delete: status='inactive'

Sale:          branch(FK), store(FK), worker(FK), customer(FK,null),
               smena(FK,null), payment_type(cash|card|mixed|debt),
               total_price, discount_amount, paid_amount, debt_amount,
               status(completed|cancelled), note, created_on

SaleItem:      sale(FK), product(FK), quantity, unit_price, total_price
               → immutable (o'zgartirilmaydi)
```

**Serializer'lar (9 ta):**
```
CustomerGroupListSerializer, CustomerGroupCreateSerializer
CustomerListSerializer, CustomerDetailSerializer
CustomerCreateSerializer, CustomerUpdateSerializer
SaleItemListSerializer, SaleItemInputSerializer
SaleCreateSerializer   ← Serializer (ModelSerializer emas — items write-only)
SaleDetailSerializer
```

**Endpointlar:**
```
GET/POST   /api/v1/customer-groups/  + GET/PATCH/DELETE /{id}/  (IsManagerOrAbove)
GET/POST   /api/v1/customers/        + GET/PATCH/DELETE /{id}/  (CanAccess('sotuv'))
GET/POST   /api/v1/sales/            + GET              /{id}/  (CanAccess('sotuv'))
PATCH      /api/v1/sales/{id}/cancel/                           (@transaction.atomic)
```

**Sale yaratish — 13 qadam (@transaction.atomic):**
1. Serializer validatsiya
2. Branch → store tekshirish
3. Customer → store tekshirish
4. Settings: `allow_cash/card/debt` tekshirish
5. Smena: `shift_enabled` bo'lsa ochiq smena bor-yo'qligi
6. `total_price` hisoblash (`unit_price` yoki `product.sale_price`)
7. Chegirma: `allow_discount` + `max_discount_percent`
8. To'lov summasi validatsiya
9. Mahsulot → store tekshirish
10. Stock: `select_for_update()` + mavjudlik tekshirish
11. `Sale.objects.create()`
12. `SaleItem` + `StockMovement(OUT)` + `Stock` → `F('quantity') - qty`
13. `Customer.debt_balance` yangilash (nasiya bo'lsa)
    + AuditLog

**Sale bekor qilish (cancel):**
- Faqat `completed` savdo bekor qilinadi
- Har SaleItem uchun `StockMovement(IN)` + `Stock` qaytariladi
- `Customer.debt_balance` kamaytiriladi (nasiya bo'lsa)
- `sale.status = 'cancelled'`

**store/views.py — `_build_report()` yangilandi:**
- Lazy import: `from trade.models import Sale, SaleStatus, PaymentType`
- `Sale.objects.filter(smena=smena, status='completed').aggregate(Sum, Count)`
- `by_payment`: cash / card / mixed / debt to'lov turlari bo'yicha

**Yangi fayllar:**
- `trade/models.py` — barcha modellar
- `trade/serializers.py` — 9 ta serializer
- `trade/views.py` — 3 ta ViewSet
- `trade/api_urls.py` — router
- `trade/migrations/0001_initial.py` — CustomerGroup, Customer, Sale, SaleItem

**Yangilangan fayllar:**
- `store/views.py` — `_build_report()` haqiqiy aggregatsiya
- `config/urls.py` — `path('api/v1/', include('trade.api_urls'))`

---

### BOSQICH 5 — SaleReturn (Qaytarish) ← YANGI
```
SaleReturn (trade app da yashaydi):
  sale(FK, null)         ← asl savdoga bog'liq (ixtiyoriy)
  branch(FK)
  worker(FK)
  customer(FK, null)
  smena(FK, null)
  reason                 ← qaytarish sababi (matn)
  total_amount
  status(pending|confirmed|cancelled)
  created_on

SaleReturnItem:
  return_obj(FK)
  product(FK)
  quantity, unit_price, total_price

→ SaleReturn CONFIRMED bo'lganda: StockMovement(IN) AVTOMATIK (mahsulot omborga qaytadi)
→ Customer.debt_balance qayta hisoblanadi (agar nasiya bo'lsa)
→ Z-report da qaytarishlar alohida ko'rsatiladi
→ Ruxsatlar: IsAuthenticated + IsManagerOrAbove (qaytarishni faqat manager tasdiqlaydi)
```

---

### BOSQICH 6 — expense app (Xarajatlar)
```
ExpenseCategory (expense app):
  name, store(FK), status

Expense (expense app):
  category(FK), branch(FK), worker(FK), smena(FK, null),
  amount, description, date, receipt_image(null, upload_to='expenses/')

→ smena yopilganda (Z-report) xarajatlar ham hisobga olinadi
→ Ruxsatlar: IsAuthenticated + CanAccess('xarajatlar')
```

---

### BOSQICH 7 — WastageRecord (Isrof / Chiqindi) ← YANGI
```
WastageRecord (warehouse app da yashaydi):
  product(FK)
  branch(FK, null)       ← yoki
  warehouse(FK, null)    ← biri majburiy (Stock constraint kabi)
  worker(FK)
  smena(FK, null)
  quantity
  reason: expired | damaged | stolen | other
  note(blank)
  date

→ WastageRecord yaratilganda: StockMovement(OUT) AVTOMATIK (reason='isrof' note da)
→ CheckConstraint: branch YOKI warehouse — faqat bittasi
→ Oylik/kunlik isrof hisoboti (Dashboard + Export)
→ Ruxsatlar: IsManagerOrAbove
```

---

### BOSQICH 8 — StockAudit (Inventarizatsiya) ← YANGI
```
StockAudit (warehouse app da yashaydi):
  branch(FK, null)       ← yoki
  warehouse(FK, null)    ← biri majburiy
  store(FK)
  worker(FK)             ← kim o'tkazdi
  status: draft | confirmed | cancelled
  note(blank)
  created_on, confirmed_on(null)

StockAuditItem:
  audit(FK)
  product(FK)
  expected_qty     ← tizim ma'lumotiga ko'ra (avtomatik)
  actual_qty       ← xodim hisobladi (qo'lda kiritiladi)
  difference       ← actual_qty - expected_qty (computed)

→ Status DRAFT: xodim mahsulotlarni sanab kiritadi
→ Status CONFIRMED: farq bo'lsa StockMovement(IN yoki OUT) AVTOMATIK
  - difference > 0 → StockMovement(IN, note='inventarizatsiya oshiqcha')
  - difference < 0 → StockMovement(OUT, note='inventarizatsiya kamomad')
→ Faqat bitta DRAFT audit bir vaqtda (unikal constraint)
→ Ruxsatlar: IsManagerOrAbove
```

---

### BOSQICH 9 — WorkerKPI ← YANGI
```
WorkerKPI (accaunt app da yashaydi):
  worker(FK), store(FK)
  month(1-12), year
  sales_count, sales_amount
  returns_count, returns_amount
  net_sales_amount     ← sales_amount - returns_amount
  target_amount        ← oylik maqsad (manager tomonidan belgilanadi)
  target_reached       ← BooleanField (net >= target)
  bonus_amount         ← bonus (agar target_reached)

unique_together: [('worker', 'month', 'year')]

→ Sale yaratilganda real-time yangilanadi (worker uchun KPI += )
→ SaleReturn tasdiqlanganda kamayadi (worker uchun KPI -= )
→ Celery oylik task (har oy 1-kuni yaratiladi)
→ Endpointlar:
  GET /api/v1/workers/{id}/kpi/?month=3&year=2026   ← 1 ta hodim
  GET /api/v1/kpi/?month=3&year=2026               ← barcha hodimlar (manager)
→ Ruxsatlar: IsManagerOrAbove
```

---

### BOSQICH 10 — Z/X-report ← YANGI
```
Z-report (smena yakunida, smena YOPILADI):
  - Jami sotuv: soni + summasi
  - To'lov turlari: naqd / karta / aralash / nasiya
  - Qaytarishlar: soni + summasi
  - Xarajatlar: kategoriya bo'yicha
  - Sof tushum (naqd kirim - naqd xarajat)
  - Hodim bo'yicha sotuv jadvali
  - Ombor harakatlari (kirim/chiqim/isrof)
  - Boshlanish va yakunlanish naqdi

X-report (smena davomida, smena YOPILMAYDI):
  - Xuddi Z-report lekin smena davom etadi
  - Istalgan vaqtda chiqariladi

Texnik:
  → trade app da Smena viewida (close action)
  → PDF (reportlab) + JSON javob
  → Endpoint: POST /api/v1/shifts/{id}/z-report/  ← yopadi + PDF
              GET  /api/v1/shifts/{id}/x-report/  ← yopilmaydi + PDF
```

---

### BOSQICH 11 — Telegram bot ← YANGI
```
Bildirishnomalar (config/telegram.py yoki alohida utility):
  - Kam qoldiq: mahsulot low_stock_threshold ga yetganda DARHOL
  - Kunlik sotuv hisoboti: har kuni kechki 20:00 (Celery beat)
  - Smena hisoboti: Z-report ma'lumotlari smena yopilganda
  - WorkerKPI: oylik natijalar (har oy 1-kuni)

Sozlash:
  StoreSettings ga qo'shiladi:
    telegram_enabled = BooleanField(default=False)
    telegram_chat_id = CharField(null=True)  ← owner o'z chat_id ni kiritadi

Texnik:
  TELEGRAM_BOT_TOKEN → env variable (settings.py da)
  httpx.post() yoki python-telegram-bot (async)
  Barcha xabarlar Celery task orqali (async, queue da)
  → requirements/base.txt ga python-telegram-bot yoki httpx qo'shiladi
```

---

### BOSQICH 12 — PriceList (Narx ro'yxati) ← YANGI
```
CustomerGroup (trade app da):
  name, store(FK), discount_percent(default=0)

PriceList (trade app da):
  product(FK), customer_group(FK), price
  store(FK), valid_from, valid_to(null)

Customer modeliga qo'shiladi:
  customer_group(FK, null)

→ Sale yaratilganda unit_price qanday aniqlanadi:
  1. Mijozning customer_group mavjudmi?
  2. Agar ha → PriceList da aktiv narx bormi?
     (valid_from ≤ today ≤ valid_to YOKI valid_to is null)
  3. Agar ha → PriceList.price ishlatiladi
  4. Agar yo'q → Product.sale_price standart narx
→ Vaqtinchalik aksiya uchun valid_to o'rnatiladi
→ Ruxsatlar: IsManagerOrAbove (narx ro'yxatini boshqarish)
```

---

### BOSQICH 13 — Supplier + PurchaseOrder (v2 — KEYINGI VERSIYA) ← KEYINGI VERSIYA
```
⚠️ BU BOSQICH KEYINGI VERSIYADA QILINADI (hozirgi versiyada emas)
⚠️ Dizayn eslab qolinsin!

Supplier (warehouse app da):
  name, phone, company, address
  store(FK), debt_balance, status

PurchaseOrder (warehouse app da):
  supplier(FK), branch(FK, null), warehouse(FK, null)
  worker(FK), status(draft|confirmed|cancelled)
  total_amount, created_on

PurchaseItem:
  order(FK), product(FK), quantity, unit_price, total_price

→ PurchaseOrder CONFIRMED bo'lganda: StockMovement(IN) AVTOMATIK
→ Supplier.debt_balance yangilanadi (qarz hisobi)
→ Celery task: qarz eslatma (haftalik)
```

---

### BOSQICH 14 — Online Kassa / OFD (v2 — KEYINGI VERSIYA) ← KEYINGI VERSIYA
```
⚠️ BU BOSQICH KEYINGI VERSIYADA QILINADI (hozirgi versiyada emas)
⚠️ O'ZBEKISTONDA 2026 YILDAN MAJBURIY — ESDAN CHIQARMA!

OFD (Online Fiskal Daftarxona) integratsiyasi:
  - Soliq.uz yoki ATIX API bilan integratsiya
  - Sale yaratilganda chek OFD ga yuboriladi (async Celery task)
  - StoreSettings.tax_enabled + tax_percent ishlatiladi
  - Fiskal kvitansiya raqami javobda qaytariladi
  - Muvaffaqiyatsiz bo'lsa → retry (3 marta), keyin manual

StoreSettings ga qo'shiladi (v2 da):
  ofd_enabled, ofd_token, ofd_device_id
```

---

### BOSQICH 15 — Celery tasks (barcha tasklar)
```
Barcha Celery tasklar config/celery.py va tasks.py da:

PERIODIC (Celery beat):
  - ExchangeRate kunlik yangilanishi  → har kuni 09:00 (CBU API)
  - Low stock tekshirish              → har 6 soatda
  - WorkerKPI oylik generatsiya       → har oy 1-kuni 00:01
  - Telegram kunlik hisobot           → har kuni 20:00
  - Telegram qarz eslatmasi (v2)      → har hafta dushanba 10:00

ASYNC (on demand):
  - Telegram xabar yuborish           → Sale/WastageRecord/StockAudit da trigger
  - OFD chek yuborish (v2)            → Sale da trigger
  - Export fayl generatsiya           → PDF/Excel so'rovi bo'lganda
```

---

### BOSQICH 16 — Export (Excel / PDF)
```
Excel (openpyxl — allaqachon o'rnatilgan):
  - Mahsulotlar ro'yxati (barcode, narx, qoldiq)
  - Kirim/chiqim/ko'chirish harakatlari
  - Savdolar hisoboti (sana oralig'i bo'yicha)
  - Xarajatlar hisoboti
  - WorkerKPI hisoboti
  - Inventarizatsiya natijasi

PDF (reportlab — allaqachon o'rnatilgan):
  - Z/X-report (smena hisoboti)
  - Sotuv cheki (receipt)
  - Inventarizatsiya natijasi
  - Savdolar hisoboti

Endpoint pattern:
  GET /api/v1/products/export/?format=excel
  GET /api/v1/shifts/{id}/z-report/?format=pdf
```

---

### BOSQICH 17 — Dashboard (Tahlil paneli)
```
Real-time ko'rsatkichlar (annotate/aggregate, N+1 YO'Q):
  - Bugungi sotuv (soni + summasi)
  - Haftalik/oylik sotuv grafigi (kunlik breakdown)
  - Top 10 mahsulot (sotuv hajmi bo'yicha)
  - Ombor holati: kam qolgan mahsulotlar (< threshold)
  - Bugungi xarajatlar (kategoriya bo'yicha)
  - Sof tushum: bugun / hafta / oy
  - Hodim samaradorligi (WorkerKPI rank)
  - Qaytarishlar foizi (returns / sales)

→ Redis kesh: 5-15 daqiqa TTL (har do'kon uchun alohida key)
→ Endpoint: GET /api/v1/dashboard/
→ Filter: ?date=2026-03-01 (aniq kun), ?period=week|month
```

---

### BOSQICH 18 — Offline rejim ← YANGI
```
Muammo: Internet uzilsa kassa to'xtaydi.
Yechim: Idempotency keys + Sync queue pattern

Backend qismi:
  - Har POST so'rovga X-Idempotency-Key header qabul qilinadi
  - Duplicate so'rovlar (bir xil key) birinchi javob qaytariladi
  - IdempotencyKey model: key, response_body, created_on (24h TTL)
  - Batch sync endpoint: POST /api/v1/sync/batch/
    Body: [{"operation": "create_sale", "data": {...}, "idempotency_key": "uuid"}, ...]

Frontend qismi (eslatma):
  - IndexedDB ga offline operatsiyalar saqlanadi
  - Internet kelganda batch sync yuboriladi

Qaysi operatsiyalar offline ishlaydi:
  - Sale yaratish ✅
  - SaleReturn ✅
  - Expense ✅
  - StockMovement (IN) ✅

→ Middleware yoki mixin orqali barcha ViewSet larga qo'shiladi
```

---

### BOSQICH 19 — QR kod + AuditLog API
```
QR kod (qrcode[pil] — allaqachon o'rnatilgan):
  - Mahsulot QR kodi → barcode/mahsulot URL embed
  - Sotuv cheki QR kodi → chek URL yoki PDF link
  - Endpoint: GET /api/v1/products/{id}/qr/  → PNG image response

AuditLog read API (accaunt app da):
  - GET /api/v1/audit-logs/  (faqat GET, IsManagerOrAbove)
  - Filter: ?user=, ?action=create|update|delete, ?model=, ?date_from=, ?date_to=
  - Sahifalash: PageNumberPagination
  - Export: GET /api/v1/audit-logs/export/?format=excel
```

---

### REJANING UMUMIY KETMA-KETLIGI (QAYTA ESLATMA)
```
0  ✅     Tayyorlov: MEDIA fayllar, CORS headers (x-idempotency-key) ← BAJARILDI
1  ✅     warehouse (SubCategory, Barcode, Currency, Celery kurs) ← BAJARILDI
2  ✅     StoreSettings (3 QOIDA! + barcha ixtiyoriy flaglar) ← BAJARILDI
3  ❌     Smena (shift)
4  ❌     trade (Customer, Sale, SaleItem)
5  ❌     SaleReturn (qaytarish)           ← YANGI
6  ❌     expense (xarajatlar)
7  ❌     WastageRecord (isrof)            ← YANGI
8  ❌     StockAudit (inventarizatsiya)    ← YANGI
9  ❌     WorkerKPI                        ← YANGI
10 ❌     Z/X-report                       ← YANGI
11 ❌     Telegram bot                     ← YANGI
12 ❌     PriceList (narx ro'yxati)        ← YANGI
13 ❌ V2  Supplier + PurchaseOrder         ← KEYINGI VERSIYA
14 ❌ V2  Online Kassa / OFD              ← KEYINGI VERSIYA (MAJBURIY 2026!)
15 ❌     Celery tasks (barcha)
16 ❌     Export (Excel/PDF)
17 ❌     Dashboard
18 ❌     Offline rejim                    ← YANGI
19 ❌     QR kod + AuditLog API

IXTIYORIY FLAGLAR (StoreSettings da, har do'kon uchun alohida):
  subcategory_enabled  → default=False (B1)
  sale_return_enabled  → default=True  (B5)
  wastage_enabled      → default=True  (B7)
  stock_audit_enabled  → default=True  (B8)
  kpi_enabled          → default=False (B9)
  price_list_enabled   → default=False (B12)
  shift_enabled        → default=False (B3) — allaqachon bor
  telegram_enabled     → default=False (B11) — allaqachon bor
  allow_debt           → default=False (B4) — allaqachon bor
  show_usd/rub_price   → default=False (B1.3) — allaqachon bor
  ofd_enabled          → default=False (B14) — v2
```

---

## MUHIM ESLATMALAR

### Worktree pattern (MAJBURIY)
- Claude worktree da ishlaydi: `.claude/worktrees/festive-kirch/`
- Branch: `claude/festive-kirch` → main ga cherry-pick
- **Har o'zgarishdan keyin:** `git commit` (worktree) → DARHOL `git cherry-pick` main branchga
- `__pycache__`, `db.sqlite3`, `.claude/settings.local.json` ni HECH QACHON commit qilma

### Virtual env
```bash
# Python executable:
C:/Users/U17/my_projects/shop_crm_system/myenv/Scripts/python.exe

# Django management commands:
myenv/Scripts/python.exe manage.py <command> --settings=config.settings.local
```

### Migration yaratish
```bash
myenv/Scripts/python.exe manage.py makemigrations appname --settings=config.settings.local
myenv/Scripts/python.exe manage.py migrate appname --settings=config.settings.local
```

### Git log (so'nggi commitlar, 03.03.2026)
```
(joriy)  feat(store): BOSQICH 2 — StoreSettings, signal, Redis cache, 10 guruh sozlamalar
1272c60  feat(warehouse): BOSQICH 1 — SubCategory, barcode EAN-13, Currency, ExchangeRate, Celery task
bc70380  feat: BOSQICH 0 bajarildi — CORS x-idempotency-key, 20-bosqichli to'liq reja
e69d660  docs: loyiha rejasi 9 bosqichdan 19 bosqichga yangilandi (worktree)
b55551b  docs: loyiha rejasi 9 bosqichdan 19 bosqichga yangilandi (main, cherry-pick)
9ce1d81  docs: 3 qoida + to'liq loyiha rejasi PROJECT_CONTEXT ga qo'shildi (main)
d1fc1b8  feat(warehouse): Product.image + WarehouseListSerializer.address (main)
9466a72  fix: 3 ta muhim xato tuzatildi — race condition, hardcoded URL, string comparison
```

### Qo'shilgan xususiyatlar (03.03.2026)
| Xususiyat | Joyi | Izoh |
|-----------|------|------|
| `Product.image` | `warehouse/models.py` | Ixtiyoriy `ImageField(upload_to='products/')` — migration 0003 |
| `WarehouseListSerializer.address` | `warehouse/serializers.py` | Ombor ro'yxatida manzil ham ko'rsatiladi |
| `CORS_ALLOW_HEADERS += 'x-idempotency-key'` | `config/settings/base.py` | Offline rejim uchun (BOSQICH 18) |
| BOSQICH 0 tayyorlov | `base.py`, `urls.py` | MEDIA fayllar allaqachon to'g'ri sozlangan — tasdiqlandi |
| 20-bosqichli loyiha rejasi | `PROJECT_CONTEXT.md` | Barcha ixtiyoriy flaglar qo'shildi |
| **BOSQICH 1** — `SubCategory` modeli | `warehouse/models.py` + migration 0004 | `Category → SubCategory → Product` ierarxiya, `StoreSettings.subcategory_enabled` |
| **BOSQICH 1** — Barcode EAN-13 auto-generate | `warehouse/utils.py`, `views.py` | `generate_unique_barcode(store_id)`, prefix `20XXXXXYYYYY` + check digit, `GET /products/{id}/barcode/?format=png\|svg` |
| **BOSQICH 1** — `Currency` + `ExchangeRate` modellari | `warehouse/models.py` + migration 0005 | UZS/USD/EUR/RUB/CNY seed, `Product.price_currency FK` |
| **BOSQICH 1** — Celery task: valyuta kursi | `warehouse/tasks.py`, `config/settings/base.py` | CBU API, `crontab(hour=9, minute=0)`, retry 3×5min |
| **BOSQICH 2** — `StoreSettings` modeli | `store/models.py` + migration 0004 | 10 guruh, 30+ maydon, OneToOne → Store |
| **BOSQICH 2** — Signal QOIDA 1 | `store/signals.py`, `store/apps.py` | `post_save(Store)` → auto `StoreSettings.get_or_create()` |
| **BOSQICH 2** — Redis kesh QOIDA 3 | `config/cache_utils.py` | `get_store_settings(store_id)` TTL=5min, `invalidate_store_settings()` |
| **BOSQICH 2** — `StoreSettingsViewSet` | `store/views.py`, `store/api_urls.py` | `GET/PATCH /api/v1/settings/`, kesh invalidatsiya perform_update da |

### Tuzatilgan xatolar (03.03.2026)
| Xato | Joyi | Tuzatish |
|------|------|---------|
| `IsSotuvchiOrAbove`: `'active'` string taqqoslash | `accaunt/permissions.py` | `WorkerStatus.ACTIVE` TextChoices constant |
| `SendPasswordResetEmailSerializer`: hardcoded `localhost:3000` URL | `accaunt/serializers.py` | `settings.FRONTEND_URL` env variable |
| `StockMovement.perform_create`: race condition | `warehouse/views.py` | `@transaction.atomic` + `select_for_update()` + `F()` expression |

---

## LOYIHA TUZILMASI

```
shop_crm_system/
├── config/
│   ├── __init__.py       ← Celery import
│   ├── celery.py         ← Celery konfiguratsiya
│   ├── cache_utils.py    ← ✅ BOSQICH 2 — QOIDA 3 (get_store_settings + invalidate)
│   ├── exceptions.py     ← ✅ Custom exception handler (o'zbek tilidagi xato xabarlari)
│   ├── middleware.py     ← HealthCheckMiddleware
│   ├── settings/
│   │   ├── base.py       ← Umumiy sozlamalar (CORS, JWT, DRF, Celery, DATETIME_FORMAT)
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
├── store/                ✅ Store, Branch (soft delete, multi-tenant, workers in detail)
│   ├── models.py         ← Store, Branch, StoreStatus; Branch unique_together(store,name)
│   ├── views.py          ← StoreViewSet, BranchViewSet
│   ├── serializers.py    ← workers detail da, status update da, _worker_short helper
│   ├── api_urls.py       ← /api/v1/stores/, /api/v1/branches/, /api/v1/settings/
│   ├── signals.py        ← ✅ BOSQICH 2 — QOIDA 1 (auto StoreSettings yaratish)
│   └── migrations/
│       ├── 0001_initial.py
│       └── 0003_alter_branch_unique_together.py ← unique_together qo'shildi
├── warehouse/            ✅ Category, Product, Stock, StockMovement
│   ├── models.py         ← Category, Product(unique_together store+name, store+barcode), Stock, StockMovement
│   ├── views.py          ← CategoryViewSet, ProductViewSet, StockViewSet, StockMovementViewSet
│   ├── serializers.py    ← 14 ta serializer (per-store unique validation)
│   ├── api_urls.py       ← /api/v1/warehouse/
│   └── migrations/
│       ├── 0001_initial.py
│       └── 0002_alter_product_unique_together.py ← unique_together qo'shildi
├── trade/                ❌ Hali boshlanmagan
├── expense/              ❌ Hali boshlanmagan
├── requirements/
│   ├── base.txt
│   └── production.txt    ← gunicorn, whitenoise, dj-database-url
├── requirements.txt      ← -r requirements/production.txt
├── Dockerfile            ← collectstatic BUILD vaqtida
└── railway.toml          ← port 8000 hardcode
```
