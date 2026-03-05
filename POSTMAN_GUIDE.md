# Shop CRM API — Postman Testing Guide

## Postman bilan avtomatik ishlash haqida

**Yo'q** — Claude to'g'ridan Postman ilovasi bilan ishlay olmaydi (Postman API yoki tooliga ega emas).
Lekin quyidagi ma'lumotlar asosida o'zingiz sozlaysiz.

---

## Sozlash (Environment Variables)

Postman'da **Environment** yarating:

| Variable  | Value                                     |
|-----------|-------------------------------------------|
| `base_url` | `http://localhost:8000`                  |
| `access`   | *(login dan keyin auto to'ldiriladi)*    |
| `refresh`  | *(login dan keyin auto to'ldiriladi)*    |

**Authorization Header (barcha protected endpoint uchun):**
```
Type: Bearer Token
Token: {{access}}
```

---

## Tavsiya etilgan test tartibi

```
1.  Register       → access va refresh tokenni saqlang
2.  Store yarating → store ID saqlang
3.  Branch yarating → branch ID saqlang
4.  Smena oching (agar shift_enabled=true) → smena ID saqlang
5.  Category + Subcategory yarating
6.  Product yarating → product ID saqlang
7.  Stock qo'shing (yoki Movement IN)
8.  Customer Group + Customer yarating
9.  Sale yarating (items da product ID ishlatilsin)
10. Sale cancel qiling
```

---

## Sinovda qidiladigan xatolar

| Holat                              | Kutilgan xato                                     |
|------------------------------------|---------------------------------------------------|
| Token yo'q                         | `401 Unauthorized`                               |
| Boshqa do'kon ma'lumoti            | `403 / 404`                                      |
| Stokda yetarli mahsulot yo'q       | `400` — `"yetarli qoldiq yo'q"`                  |
| Smena yopiq, sotuv qilmoq          | `400` — `"ochiq smena yo'q"`                     |
| paid_amount noto'g'ri              | `400` — `"To'lov summasi jami narxga teng bo'lishi shart"` |
| Register: username band            | `400` — `"Bu login allaqachon band"`             |

---

## Standart javob formati

| Metod    | Status | Javob formati                       |
|----------|--------|-------------------------------------|
| `create` | 201    | `{"message": "...", "data": {...}}` |
| `update` | 200    | `{"message": "...", "data": {...}}` |
| `destroy`| 200    | `{"message": "..."}`                |
| `list`   | 200    | `[...]`                             |
| `retrieve`| 200   | `{...}`                             |

---

## 1. AUTH (`/api/v1/auth/`)

### 1.1 Register
```
POST {{base_url}}/api/v1/auth/register/
Auth: None (public)

Body (JSON):
{
    "username":   "owner1",
    "first_name": "Ulugbek",
    "last_name":  "Xatamjonov",
    "email":      "owner@example.com",
    "phone1":     "+998901234567",
    "phone2":     "",           // optional
    "password":   "Pass1234!",
    "password2":  "Pass1234!"
}

Response 201:
{
    "message": "Ro'yxatdan muvaffaqiyatli o'tdingiz!",
    "tokens": {
        "refresh": "...",
        "access":  "..."
    }
}
```

> **Postman → Tests tab** — tokenlarni avtomatik saqlash:
> ```javascript
> const res = pm.response.json();
> pm.environment.set("access",  res.tokens.access);
> pm.environment.set("refresh", res.tokens.refresh);
> ```

---

### 1.2 Login
```
POST {{base_url}}/api/v1/auth/login/
Auth: None (public)

Body (JSON):
{
    "username": "owner1",
    "password": "Pass1234!"
}

Response 200:
{
    "access":  "...",
    "refresh": "...",
    "user": {
        "id":         1,
        "username":   "owner1",
        "first_name": "Ulugbek",
        "last_name":  "Xatamjonov",
        "email":      "...",
        "phone1":     "...",
        "worker": {
            "id":          1,
            "role":        "owner",
            "store":       null,
            "branch":      null,
            "permissions": [...]
        }
    }
}
```

> **Postman → Tests tab:**
> ```javascript
> const res = pm.response.json();
> pm.environment.set("access",  res.access);
> pm.environment.set("refresh", res.refresh);
> ```

---

### 1.3 Logout
```
POST {{base_url}}/api/v1/auth/logout/
Auth: Bearer {{access}}

Body (JSON):
{
    "refresh": "{{refresh}}"
}

Response 200:
{
    "message": "Tizimdan muvaffaqiyatli chiqdingiz!"
}
```

---

### 1.4 Change Password
```
POST {{base_url}}/api/v1/auth/change-password/
Auth: Bearer {{access}}

Body (JSON):
{
    "current_password": "Pass1234!",
    "password":         "NewPass5678!",
    "password2":        "NewPass5678!"
}

Response 200:
{
    "message": "Parol muvaffaqiyatli o'zgartirildi!"
}
```

---

### 1.5 My Profile — Ko'rish
```
GET {{base_url}}/api/v1/auth/profil/
Auth: Bearer {{access}}

Response 200:
{
    "id":         1,
    "username":   "owner1",
    "first_name": "Ulugbek",
    "last_name":  "Xatamjonov",
    "email":      "...",
    "phone1":     "...",
    "phone2":     null,
    "worker":     { ... }
}
```

---

### 1.6 My Profile — Yangilash
```
PATCH {{base_url}}/api/v1/auth/profil/
Auth: Bearer {{access}}

Body (JSON) — faqat o'zgartirmoqchi bo'lgan maydon:
{
    "first_name": "Ulug'bek",
    "phone1":     "+998901111111"
}

Response 200:
{
    "message": "Profil muvaffaqiyatli yangilandi.",
    "data": { ... }
}
```

---

### 1.7 Send Reset Email
```
POST {{base_url}}/api/v1/auth/send-reset-email/
Auth: None

Body (JSON):
{
    "email": "owner@example.com"
}

Response 200:
{
    "message": "Parolni tiklash uchun havola emailga yuborildi."
}
```

---

### 1.8 Reset Password
```
POST {{base_url}}/api/v1/auth/reset-password/<uid>/<token>/
Auth: None
// uid va token — emaildagi havoladan olinadi

Body (JSON):
{
    "password":  "NewPass5678!",
    "password2": "NewPass5678!"
}

Response 200:
{
    "message": "Parol muvaffaqiyatli o'zgartirildi!"
}
```

---

## 2. WORKERS (`/api/v1/workers/`)

> **Ruxsatlar:** `list/retrieve` → manager+; `create/update/delete` → faqat owner

### 2.1 List Workers
```
GET {{base_url}}/api/v1/workers/
Auth: Bearer {{access}}

Query Params (ixtiyoriy):
?status=active|tatil|ishdan_ketgan
?role=owner|manager|seller
?branch=<branch_id>
?search=<ism yoki telefon>

Response 200: [ { id, user, role, branch, salary, status } ]
```

---

### 2.2 Create Worker
```
POST {{base_url}}/api/v1/workers/
Auth: Bearer {{access}}   // faqat owner

Body (JSON):
{
    "username":   "seller1",
    "first_name": "Ali",
    "last_name":  "Valiyev",
    "email":      "seller@example.com",
    "phone1":     "+998901234568",
    "password":   "Pass1234!",
    "password2":  "Pass1234!",
    "role":       "seller",             // owner | manager | seller
    "branch":     1,                    // branch ID (shu do'konniki bo'lishi kerak)
    "salary":     "3000000.00",         // optional
    "permissions": ["sotuv", "ombor"]   // optional
}

Response 201:
{
    "message": "Yangi hodim muvaffaqiyatli qo'shildi!",
    "data": { ... }
}
```

---

### 2.3 Get Worker Detail
```
GET {{base_url}}/api/v1/workers/1/
Auth: Bearer {{access}}

Response 200: { id, user, role, branch, store, salary, permissions, status, ... }
```

---

### 2.4 Update Worker
```
PATCH {{base_url}}/api/v1/workers/1/
Auth: Bearer {{access}}   // faqat owner

Body (JSON) — faqat o'zgartirmoqchi bo'lgan:
{
    "first_name":  "Alisher",
    "role":        "manager",
    "salary":      "5000000.00",
    "permissions": ["sotuv", "ombor", "sozlamalar"]
}

Response 200:
{
    "message": "Hodim ma'lumotlari muvaffaqiyatli yangilandi.",
    "data": { ... }
}
```

---

### 2.5 Delete Worker
```
DELETE {{base_url}}/api/v1/workers/1/
Auth: Bearer {{access}}   // faqat owner
// DIQQAT: hard delete — user va worker ikkalasi o'chadi!

Response 200:
{
    "message": "Hodim muvaffaqiyatli o'chirildi."
}
```

---

## 3. STORES (`/api/v1/stores/`)

> **Ruxsatlar:** barcha → IsAuthenticated; write → faqat owner

### 3.1 Create Store
```
POST {{base_url}}/api/v1/stores/
Auth: Bearer {{access}}

Body (JSON):
{
    "name":        "Mening Do'konim",
    "address":     "Toshkent, Chilonzor",
    "phone":       "+998901234567",
    "description": "Elektronika do'koni"   // optional
}

Response 201:
{
    "message": "Do'kon muvaffaqiyatli yaratildi.",
    "data": { id, name, address, phone, description, branches: [], workers: [] }
}
// Signal avtomatik: StoreSettings va Subscription (trial 30 kun) yaratadi
```

---

### 3.2 List Stores
```
GET {{base_url}}/api/v1/stores/
Auth: Bearer {{access}}

Response 200: [ { id, name, address, is_active } ]
```

---

### 3.3 Get Store Detail
```
GET {{base_url}}/api/v1/stores/1/
Auth: Bearer {{access}}

Response 200: { id, name, address, phone, branches: [...], workers: [...] }
```

---

### 3.4 Update Store
```
PATCH {{base_url}}/api/v1/stores/1/
Auth: Bearer {{access}}

Body (JSON):
{
    "name":    "Yangilangan Do'kon Nomi",
    "address": "Yangi manzil"
}

Response 200:
{
    "message": "Do'kon muvaffaqiyatli yangilandi.",
    "data": { ... }
}
```

---

### 3.5 Delete Store (Soft)
```
DELETE {{base_url}}/api/v1/stores/1/
Auth: Bearer {{access}}

Response 200:
{
    "message": "Do'kon nofaol qilindi."
}
// is_active=False bo'ladi, ma'lumotlar o'chmaydi
```

---

## 4. BRANCHES (`/api/v1/branches/`)

### 4.1 Create Branch
```
POST {{base_url}}/api/v1/branches/
Auth: Bearer {{access}}

Body (JSON):
{
    "name":    "Markaziy Filial",
    "address": "Toshkent, Yunusobod",
    "phone":   "+998901234567"   // optional
}

Response 201:
{
    "message": "Filial muvaffaqiyatli yaratildi.",
    "data": { id, name, address, store, is_active }
}
```

---

### 4.2 List Branches
```
GET {{base_url}}/api/v1/branches/
Auth: Bearer {{access}}

Response 200: [ { id, name, address, store, is_active } ]
```

---

### 4.3 Get Branch Detail
```
GET {{base_url}}/api/v1/branches/1/
Auth: Bearer {{access}}

Response 200: { id, name, address, store, workers: [...], is_active }
```

---

### 4.4 Update Branch
```
PATCH {{base_url}}/api/v1/branches/1/
Auth: Bearer {{access}}

Body (JSON):
{
    "name":    "Shimoliy Filial",
    "address": "Toshkent, Shayxontohur"
}

Response 200:
{
    "message": "Filial muvaffaqiyatli yangilandi.",
    "data": { ... }
}
```

---

### 4.5 Delete Branch (Soft)
```
DELETE {{base_url}}/api/v1/branches/1/
Auth: Bearer {{access}}

Response 200:
{
    "message": "Filial nofaol qilindi."
}
```

---

## 5. SETTINGS (`/api/v1/settings/`)

> Signal avtomatik yaratadi — `create` va `delete` endpoint YO'Q

### 5.1 Get Settings
```
GET {{base_url}}/api/v1/settings/
Auth: Bearer {{access}}   // CanAccess('sozlamalar')

Response 200:
[
    {
        "id":                   1,
        "store":                1,
        "allow_cash":           true,
        "allow_card":           true,
        "allow_debt":           false,
        "allow_discount":       true,
        "max_discount_percent": "10.00",
        "shift_enabled":        true,
        "low_stock_alert":      true,
        "low_stock_threshold":  "5.000",
        ...
    }
]
```

---

### 5.2 Update Settings
```
PATCH {{base_url}}/api/v1/settings/1/
Auth: Bearer {{access}}   // faqat owner

Body (JSON) — faqat o'zgartirmoqchi bo'lgan:
{
    "allow_debt":           true,
    "max_discount_percent": "15.00",
    "shift_enabled":        false
}

Response 200:
{
    "message": "Sozlamalar muvaffaqiyatli yangilandi.",
    "data": { ... }
}
```

---

## 6. SHIFTS / SMENA (`/api/v1/shifts/`)

### 6.1 Open Shift (Smena ochish)
```
POST {{base_url}}/api/v1/shifts/
Auth: Bearer {{access}}

Body (JSON):
{
    "branch":       1,
    "opening_cash": "500000.00"   // optional, default 0
}

Response 201:
{
    "message": "Smena muvaffaqiyatli ochildi.",
    "data": { id, branch, status: "open", opened_by, opened_at, opening_cash }
}
```

---

### 6.2 List Shifts
```
GET {{base_url}}/api/v1/shifts/
Auth: Bearer {{access}}

Query Params:
?status=open|closed
?branch=<branch_id>

Response 200: [ { id, branch, status, opened_at, closed_at } ]
```

---

### 6.3 Get Shift Detail
```
GET {{base_url}}/api/v1/shifts/1/
Auth: Bearer {{access}}

Response 200: { id, branch, status, opened_by, opening_cash, sales_summary, ... }
```

---

### 6.4 Close Shift (Z-report)
```
PATCH {{base_url}}/api/v1/shifts/1/close/
Auth: Bearer {{access}}   // manager+

Body (JSON):
{
    "closing_cash": "1500000.00"   // optional
}

Response 200:
{
    "message": "Smena yopildi.",
    "data": { ... z-report ma'lumotlari ... }
}
```

---

### 6.5 X-Report (smena yopilmaydi)
```
GET {{base_url}}/api/v1/shifts/1/x-report/
Auth: Bearer {{access}}

Response 200:
{
    "smena_id":   1,
    "branch":     "Markaziy Filial",
    "cash_sales": "...",
    "card_sales": "...",
    "total":      "...",
    ...
}
```

---

## 7. WAREHOUSE — Categories (`/api/v1/warehouse/categories/`)

### 7.1 Create Category
```
POST {{base_url}}/api/v1/warehouse/categories/
Auth: Bearer {{access}}

Body (JSON):
{
    "name": "Elektronika"
}

Response 201:
{
    "message": "Kategoriya muvaffaqiyatli yaratildi.",
    "data": { id, name, is_active }
}
```

---

### 7.2 List / Detail / Update / Delete
```
GET    {{base_url}}/api/v1/warehouse/categories/
GET    {{base_url}}/api/v1/warehouse/categories/1/
PATCH  {{base_url}}/api/v1/warehouse/categories/1/   → Body: { "name": "Yangi nom" }
DELETE {{base_url}}/api/v1/warehouse/categories/1/   → soft delete (is_active=False)
```

---

## 8. WAREHOUSE — SubCategories (`/api/v1/warehouse/subcategories/`)

### 8.1 Create SubCategory
```
POST {{base_url}}/api/v1/warehouse/subcategories/
Auth: Bearer {{access}}

Body (JSON):
{
    "name":     "Smartfonlar",
    "category": 1   // Category ID
}

Response 201:
{
    "message": "Subkategoriya muvaffaqiyatli yaratildi.",
    "data": { id, name, category, category_name }
}
```

---

### 8.2 List (filter bilan)
```
GET {{base_url}}/api/v1/warehouse/subcategories/?category=1
Auth: Bearer {{access}}

Response 200: [ { id, name, category, category_name } ]
```

---

## 9. WAREHOUSE — Currencies (`/api/v1/warehouse/currencies/`)

### 9.1 Create Currency
```
POST {{base_url}}/api/v1/warehouse/currencies/
Auth: Bearer {{access}}   // manager+

Body (JSON):
{
    "code":   "USD",
    "name":   "AQSH dollari",
    "symbol": "$"
}

Response 201:
{
    "message": "Valyuta muvaffaqiyatli qo'shildi.",
    "data": { id, code, name, symbol, latest_rate }
}
```

---

### 9.2 List / Detail
```
GET {{base_url}}/api/v1/warehouse/currencies/
GET {{base_url}}/api/v1/warehouse/currencies/1/   // latest_rate bilan
```

---

## 10. WAREHOUSE — Exchange Rates (`/api/v1/warehouse/exchange-rates/`)

### 10.1 Add Rate
```
POST {{base_url}}/api/v1/warehouse/exchange-rates/
Auth: Bearer {{access}}   // manager+

Body (JSON):
{
    "currency": 1,
    "rate":     "12850.00",
    "date":     "2026-03-05"   // optional, default today
}

Response 201:
{
    "message": "Kurs muvaffaqiyatli qo'shildi.",
    "data": { id, currency, currency_code, rate, date }
}
```

---

### 10.2 List (filter bilan)
```
GET {{base_url}}/api/v1/warehouse/exchange-rates/
?currency=USD
?date=2026-03-05

Response 200: [ { id, currency, rate, date } ]
```

---

## 11. WAREHOUSE — Products (`/api/v1/warehouse/products/`)

### 11.1 Create Product
```
POST {{base_url}}/api/v1/warehouse/products/
Auth: Bearer {{access}}
Content-Type: multipart/form-data   // rasm yuklansa

Body (form-data yoki JSON):
{
    "name":           "iPhone 15",
    "category":       1,
    "subcategory":    2,             // optional
    "unit":           "piece",       // piece | kg | litre | meter | box
    "cost_price":     "12000000.00",
    "sale_price":     "14000000.00",
    "price_currency": 1,             // Currency ID (optional, default UZS)
    "barcode":        "",            // bo'sh qolsa — auto EAN-13 generate qilinadi
    "description":    "",            // optional
    "image":          <file>         // optional (form-data da)
}

Response 201:
{
    "message": "Mahsulot muvaffaqiyatli yaratildi.",
    "data": { id, name, barcode, cost_price, sale_price, unit, status, image, ... }
}
```

---

### 11.2 List Products (filter bilan)
```
GET {{base_url}}/api/v1/warehouse/products/
?category=<id>
?subcategory=<id>
?status=active|inactive

Response 200: [ { id, name, barcode, sale_price, unit, status } ]
```

---

### 11.3 Update Product
```
PATCH {{base_url}}/api/v1/warehouse/products/1/
Auth: Bearer {{access}}

Body (JSON yoki form-data):
{
    "sale_price":  "15000000.00",
    "description": "Yangilangan tavsif"
}

Response 200:
{
    "message": "Mahsulot muvaffaqiyatli yangilandi.",
    "data": { ... }
}
```

---

### 11.4 Delete Product (Soft)
```
DELETE {{base_url}}/api/v1/warehouse/products/1/
Auth: Bearer {{access}}

Response 200:
{
    "message": "Mahsulot nofaol qilindi."
}
```

---

### 11.5 Get Barcode Image
```
GET {{base_url}}/api/v1/warehouse/products/1/barcode/
Auth: Bearer {{access}}
// Default: PNG rasm

GET {{base_url}}/api/v1/warehouse/products/1/barcode/?format=svg
// SVG format

Response: PNG yoki SVG rasm (Content-Type: image/png | image/svg+xml)
// Postman da "Send and Download" tugmasini bosing
```

---

## 12. WAREHOUSE — Stocks (`/api/v1/warehouse/stocks/`)

### 12.1 Create Stock
```
POST {{base_url}}/api/v1/warehouse/stocks/
Auth: Bearer {{access}}

Body (JSON):
{
    "product":  1,
    "branch":   1,
    "quantity": "100.000"
}

Response 201:
{
    "message": "Qoldiq muvaffaqiyatli qo'shildi.",
    "data": { id, product, product_name, branch, quantity }
}
```

---

### 12.2 List / Detail / Update
```
GET   {{base_url}}/api/v1/warehouse/stocks/
GET   {{base_url}}/api/v1/warehouse/stocks/1/
PATCH {{base_url}}/api/v1/warehouse/stocks/1/   → Body: { "quantity": "150.000" }
```

---

## 13. WAREHOUSE — Stock Movements (`/api/v1/warehouse/movements/`)

### 13.1 Create Movement (Kirim / Chiqim)
```
POST {{base_url}}/api/v1/warehouse/movements/
Auth: Bearer {{access}}

Body (JSON):
{
    "product":       1,
    "branch":        1,
    "movement_type": "in",           // in | out
    "quantity":      "50.000",
    "note":          "Yangi tovar"   // optional
}

// "in"  → Stock oshadi
// "out" → Stock kamayadi (yetarli bo'lmasa 400 xato)

Response 201:
{
    "message": "Harakat muvaffaqiyatli qayd etildi.",
    "data": { id, product, branch, movement_type, quantity, worker, created_on }
}
```

---

### 13.2 List Movements
```
GET {{base_url}}/api/v1/warehouse/movements/
Auth: Bearer {{access}}

Response 200:
[ { id, product_name, branch_name, movement_type, quantity, worker_name, created_on } ]
```

---

## 14. TRADE — Customer Groups (`/api/v1/customer-groups/`)

> **Ruxsatlar:** `list/retrieve` → IsAuthenticated; `create/update/delete` → manager+

### 14.1 Create Group
```
POST {{base_url}}/api/v1/customer-groups/
Auth: Bearer {{access}}

Body (JSON):
{
    "name":     "VIP Mijozlar",
    "discount": "5.00"   // optional, 0–100 oralig'ida foiz
}

Response 201:
{
    "message": "Mijoz guruhi muvaffaqiyatli yaratildi.",
    "data": { id, name, discount, created_on }
}
```

---

### 14.2 List / Detail
```
GET {{base_url}}/api/v1/customer-groups/
GET {{base_url}}/api/v1/customer-groups/1/
```

---

### 14.3 Update / Delete
```
PATCH  {{base_url}}/api/v1/customer-groups/1/  → Body: { "discount": "10.00" }
DELETE {{base_url}}/api/v1/customer-groups/1/
// Delete: bog'liq mijozlarda group=NULL bo'ladi (SET_NULL)
```

---

## 15. TRADE — Customers (`/api/v1/customers/`)

> **Ruxsatlar:** CanAccess('sotuv'); delete → manager+

### 15.1 Create Customer
```
POST {{base_url}}/api/v1/customers/
Auth: Bearer {{access}}

Body (JSON):
{
    "name":    "Bobur Rahimov",
    "phone":   "+998901234567",   // optional
    "address": "Toshkent",        // optional
    "group":   1                  // optional — CustomerGroup ID
}

Response 201:
{
    "message": "Mijoz muvaffaqiyatli yaratildi.",
    "data": { id, name, phone, address, debt_balance, group, group_name, status }
}
```

---

### 15.2 List Customers (filter bilan)
```
GET {{base_url}}/api/v1/customers/
?status=active|inactive
?group=<group_id>
?search=<ism yoki telefon>

Response 200: [ { id, name, phone, debt_balance, group, status } ]
```

---

### 15.3 Update Customer
```
PATCH {{base_url}}/api/v1/customers/1/
Auth: Bearer {{access}}

Body (JSON):
{
    "name":    "Yangi ism",
    "phone":   "+998909876543",
    "group":   2,
    "status":  "inactive"   // active | inactive
}

Response 200:
{
    "message": "Mijoz muvaffaqiyatli yangilandi.",
    "data": { ... }
}
```

---

### 15.4 Soft Delete
```
DELETE {{base_url}}/api/v1/customers/1/
Auth: Bearer {{access}}   // manager+

Response 200:
{
    "message": "Mijoz nofaol qilindi."
}
// status='inactive' bo'ladi, ma'lumotlar o'chmaydi
```

---

## 16. TRADE — Sales (`/api/v1/sales/`)

> **Ruxsatlar:** `list/retrieve/create` → CanAccess('sotuv'); `cancel` → manager+

### 16.1 Create Sale ⭐ (eng murakkab)
```
POST {{base_url}}/api/v1/sales/
Auth: Bearer {{access}}

Body (JSON):
{
    "branch":          1,
    "customer":        1,              // optional — null bo'lishi mumkin
    "payment_type":    "cash",         // cash | card | mixed | debt
    "discount_amount": "0.00",         // optional, default 0
    "paid_amount":     "28000000.00",
    "note":            "",             // optional
    "items": [
        {
            "product":    1,
            "quantity":   "2.000",
            "unit_price": "14000000.00"  // optional — bo'sh bo'lsa product.sale_price ishlatiladi
        },
        {
            "product":  2,
            "quantity": "1.000"
        }
    ]
}

// payment_type qoidalari:
// cash / card → paid_amount AYNAN total - discount ga teng bo'lishi SHART
// mixed       → paid_amount < total - discount (partial to'lov)
// debt        → paid_amount < total - discount (farqi customer.debt_balance ga qo'shiladi)

Response 201:
{
    "message": "Sotuv muvaffaqiyatli amalga oshirildi.",
    "data": {
        "id":               1,
        "branch":           1,
        "branch_name":      "Markaziy Filial",
        "worker_name":      "Ulugbek Xatamjonov",
        "customer":         1,
        "customer_name":    "Bobur Rahimov",
        "payment_type":     "cash",
        "total_price":      "28000000.00",
        "discount_amount":  "0.00",
        "paid_amount":      "28000000.00",
        "debt_amount":      "0.00",
        "status":           "completed",
        "items": [
            {
                "id":           1,
                "product":      1,
                "product_name": "iPhone 15",
                "unit":         "Dona",
                "quantity":     "2.000",
                "unit_price":   "14000000.00",
                "total_price":  "28000000.00"
            }
        ],
        "created_on": "2026-03-05T10:30:00Z"
    }
}
```

> **Ichki jarayon (atomic transaction):**
> 1. Branch va Customer do'konga tegishliligini tekshiradi
> 2. StoreSettings dan to'lov turi va chegirma ruxsatini tekshiradi
> 3. Agar `shift_enabled=true` — ochiq smena bor-yo'qligini tekshiradi
> 4. Har bir mahsulot stokda yetarlimi — `select_for_update` bilan tekshiradi
> 5. Sale + SaleItem saqlaydi
> 6. Har bir mahsulot uchun `StockMovement(OUT)` yaratadi va stockni kamaytiradi
> 7. Agar nasiya bo'lsa — `Customer.debt_balance` oshadi
> 8. AuditLog yozadi

---

### 16.2 List Sales (filter bilan)
```
GET {{base_url}}/api/v1/sales/
?date=2026-03-05
?branch=<branch_id>
?payment_type=cash|card|mixed|debt
?status=completed|cancelled
?customer=<customer_id>

Response 200:
[ { id, branch_name, worker_name, customer_name, payment_type, total_price, status, created_on } ]
```

---

### 16.3 Get Sale Detail
```
GET {{base_url}}/api/v1/sales/1/
Auth: Bearer {{access}}

Response 200: { ... to'liq ma'lumot + items [...] }
```

---

### 16.4 Cancel Sale
```
PATCH {{base_url}}/api/v1/sales/1/cancel/
Auth: Bearer {{access}}   // manager+

Body: {}   // bo'sh body yuborish kifoya

Response 200:
{
    "message": "Sotuv bekor qilindi.",
    "data": { ..., "status": "cancelled" }
}

// Ichki jarayon:
// - Har bir mahsulot stokka qaytariladi (StockMovement IN)
// - Agar nasiya bo'lsa — customer.debt_balance kamayadi
// - sale.status = 'cancelled'
// ESLATMA: Allaqachon bekor qilingan savdoni qayta bekor qilib bo'lmaydi (400 xato)
```

---

*Faqat tugallangan BOSQICH 0–4 qamrab olingan:*
*accaunt (auth + workers), store (stores + branches + settings + shifts),*
*warehouse (categories + subcategories + currencies + exchange-rates + products + stocks + movements),*
*trade (customer-groups + customers + sales)*
