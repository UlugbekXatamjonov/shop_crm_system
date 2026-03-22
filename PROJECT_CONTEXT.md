# CLAUDE UCHUN ESLATMA — Yangi chatda bu faylni o'qi va davom et

## 📅 22.03.2026 SESSION — QILINGAN ISHLAR

### 1. SaleItem — Ikki qatlamli chegirma arxitekturasi ✅

**Muammo:** SaleItem.unit_price va total_price chegirmasiz original narxda saqlanayotgan edi.
Bu holda foyda hisobi, margin %, top mahsulotlar hisoboti — hammasi noto'g'ri edi.

**Yechim — Variant B (Proportional Distribution):**
Savdo chegirmasi (Sale.discount_amount) har bir SaleItem ga proporsional taqsimlanadi.

**Qo'shimcha yechim — Katalog chegirma tracking:**
Mahsulotga xos katalog chegirmasini (20% kabi) alohida saqlash imkoniyati qo'shildi.

#### O'zgartirilgan fayllar:

**`trade/models.py`** — SaleItem ga 3 yangi maydon:
```python
original_price    # katalog narxi (chegirmasiz asl narx), null=True
item_discount_pct # mahsulot chegirma %, default=0
item_discount_amt # chegirma summasi (birlik uchun), null=True
unit_price        # YAKUNIY narx (barcha chegirmalardan keyin) — o'zgartirildi
total_price       # YAKUNIY jami (qty × unit_price) — o'zgartirildi
```

**`trade/serializers.py`** — ikki joyda o'zgartirish:
- `SaleItemInputSerializer` — `original_price` va `item_discount_pct` optional qo'shildi + validate()
- `SaleItemListSerializer` — yangi maydonlar response da ko'rinadi

**`trade/views.py`** — `SaleViewSet.create()` da narx hisoblash logikasi:
```
1-qatlam (katalog chegirma):
  original_price berilsa → item_discount_amt = original_price × pct / 100
                           unit_price_before_sale = original_price - item_discount_amt
  berilmasa           → unit_price frontenddan yoki product.sale_price

2-qatlam (savdo chegirma — Variant B):
  ratio = net_price / total_price
  Har item: eff_total = item_total × ratio  (oxirgi item = net_price - running_total)
  unit_price = eff_total / quantity
```

**`store/views.py`** — Z-report fix:
```python
# OLDIN (NOTO'G'RI):
sales_total = Sum('total_price')                    # 100k gross ❌

# KEYIN (TO'G'RI):
sales_total = Sum(F('total_price') - F('discount_amount'))  # 90k real ✅
```

#### Yangi migration:
- `trade/migrations/0005_saleitem_discount_fields.py`
  - AddField: `item_discount_amt`, `item_discount_pct`, `original_price`
  - AlterField: `unit_price`, `total_price` (verbose_name yangilandi)

#### Postmanda o'zgarish:

**Katalog chegirmali mahsulot (yangi variant):**
```json
{
  "product": 1, "quantity": 1,
  "original_price": 30000,
  "item_discount_pct": 20
}
```

**Oddiy mahsulot (oldingi kabi ishlaydi):**
```json
{
  "product": 2, "quantity": 1,
  "unit_price": 20000
}
```

#### Hisobotlarda nima yaxshilandi:
- Foyda hisobi to'g'ri (SaleItem.total_price endi real narx)
- Margin % to'g'ri
- Top foydali mahsulotlar to'g'ri
- Z-report tushum to'g'ri (discount ayiriladi)
- Qaytarishda xaridorga to'g'ri summa qaytariladi

### 2. Muammo analizi — aralash to'lov (MIXED) ✅

**Qaror:** MIXED to'lov faqat naqd + karta (debt aralashtirmaymiz).
Hozirgi kod to'g'ri — MIXED da `debt_amount = 0` qoladi.

---

## 📅 21.03.2026 SESSION — QILINGAN ISHLAR

### 1. `note` → `description` — to'liq o'zgartirish ✅

Barcha modellarda `note` maydoni `description` ga o'zgartirildi:
- **Store:** `Smena.description`
- **Warehouse:** `StockMovement`, `Transfer`, `TransferItem`, `WastageRecord`, `StockAudit`, `Supplier`, `SupplierPayment`
- **Trade:** `Sale.description`
- **Subscription:** `SubscriptionInvoice`, `SubscriptionDowngradeLog`

Migration fayllari: `RenameField` (ma'lumot yo'qotilmaydi)
Serializer, view, utils — barcha joyda yangilandi.

### 2. API Throttling — professional darajada ✅

**Yangi fayl:** `accaunt/throttles.py`
- `LoginThrottle` (5/min), `RegisterThrottle` (3/min), `PasswordResetThrottle` (3/hour)
- `ExportThrottle` (10/min), `BulkOperationThrottle` (20/min)

**Qo'llanilgan joylari:**
- `accaunt/views.py` — Login, Register, PasswordReset
- `export/views.py` — barcha 5 ta export va 5 ta import view
- `warehouse/views.py` — `bulk_qr`, `bulk_price_update` (get_throttles override)

**config/settings/base.py** — `DEFAULT_THROTTLE_RATES` yangilandi.

### 3. `QR_BULK_MAX_PRODUCTS = 500` settings ga ko'chirildi ✅

`warehouse/views.py` da hardcoded `500` → `settings.QR_BULK_MAX_PRODUCTS`

### 4. Bulk mahsulot narxi yangilash ✅

**Yangi endpoint:**
```
PATCH /api/v1/warehouse/products/bulk-price-update/
Body: {"items": [{"id": 5, "sale_price": 15000}, {"id": 8, "sale_price": 22000}]}
```
- Atomic transaction — xato bo'lsa rollback
- Har mahsulot uchun AuditLog (`field: sale_price`, `old/new`, `bulk: true`)
- BulkOperationThrottle orqali himoyalangan

### 5. Sotuv chek PDF ✅

**Yangi endpoint:**
```
GET /api/v1/sales/{id}/receipt/
```
- 80 mm termik printer uslubi (narrow format)
- Sarlavha: Do'kon nomi, filial, kassir, sana
- Mahsulotlar jadvali (nomi, miqdor, narx, jami)
- Jami, chegirma, to'lov summasi, qarz
- Yaratilgan: `export/utils/pdf.py` → `make_receipt_pdf()` funksiyasi

### 6. Django admin panels yaxshilandi ✅

`store/admin.py` — to'liq qayta yozildi:
- `StoreAdmin` — search, filter, ordering
- `BranchAdmin` — store autocomplete
- `StoreSettingsAdmin` — 8 ta grouped fieldsets (Funksiyalar, To'lov, Valyuta, Chek, Smena, Soliq, Telegram, OFD)
- `SmenaAdmin` — date_hierarchy, readonly_fields

### 7. config/celery.py — print→logger ✅

`print(f'Celery...')` → `logger.info('Celery...')` (professional logging)

---

## 📅 19.03.2026 SESSION #2 — QILINGAN ISHLAR

### 1. postman_test_guide.txt → PROJECT_CONTEXT.md ga ko'chirildi ✅

**Tavsif:** Barcha Postman test qo'llanmasi (1945 qator, 27 bosqich, 54 qadam, 90+ endpoint)
alohida fayldan PROJECT_CONTEXT.md ga birlashtirildi.

**O'zgartirilgan fayl:** `PROJECT_CONTEXT.md`
- Yangi bo'lim: `## POSTMAN TEST QO'LLANMASI` qo'shildi
- 1945 qator content qo'shildi

**O'chirilgan fayl:** `postman_test_guide.txt`
- Barcha ma'lumotlar PROJECT_CONTEXT.md ga ko'chgani uchun eski fayl o'chirildi

**Commit:** `ff2cd22`

---

## 📅 19.03.2026 SESSION — QILINGAN ISHLAR

### 1. Product image maydonini ro'yxatga qo'shish ✅

**O'zgartirilgan fayl:** `warehouse/serializers.py`
- `ProductListSerializer.fields` ga `image` qo'shildi

### 2. currency_code null bo'lganda yo'qolib ketish muammosi tuzatildi ✅

**Muammo:** `price_currency` null bo'lgan mahsulotlarda `currency_code`, `currency_id`, `currency_symbol` maydonlari response dan butunlay yo'qolardi.

**Sabab:** `CharField(source='price_currency.code')` — FK null bo'lganda DRF `SkipField` exception tashlaydi → maydon response ga kirmaydi.

**Yechim:** `SerializerMethodField` ga o'tkazildi — null check bilan:
```python
currency_code = serializers.SerializerMethodField()
def get_currency_code(self, obj):
    return obj.price_currency.code if obj.price_currency else None
```
`ProductListSerializer` va `ProductDetailSerializer` da ham tuzatildi.

### 3. barcode_image_url mahsulot ro'yxatiga qo'shildi ✅

**O'zgartirilgan fayl:** `warehouse/serializers.py`
- `ProductListSerializer` ga `barcode_image_url = SerializerMethodField()` qo'shildi
- `get_barcode_image_url()`: `request.build_absolute_uri(f'/api/v1/warehouse/products/{obj.id}/barcode/')`

### 4. currency_code matn orqali mahsulot yaratish/yangilash ✅

**Muammo:** Faqat `price_currency` (ID) qabul qilinar edi — frontend "USD", "UZS" kabi kod yubormoqchi edi.

**Yechim:** `ProductCreateSerializer` va `ProductUpdateSerializer` ga `currency_code` write-only field qo'shildi.
- `validate()` da: `Currency.objects.get(code=currency_code.upper())` → `price_currency` ga joylashadi
- `price_currency` yoki `currency_code` dan biri yetarli, ikkinchisi shart emas

### 5. Inactive kategoriyaning subkategoriyalari yashirildi ✅

**Muammo:** Kategoriya `status='inactive'` bo'lganda ham uning subkategoriyalari ro'yxatda ko'rinardi.

**Yechim (filter-based):** `SubCategoryViewSet.get_queryset()` ga `category__status='active'` filter qo'shildi.
- DB o'zgartirilmadi — faqat queryset filtri
- Kategoriya qayta faollashtirilsa, subkategoriyalar avtomatik ko'rinadi

### 6. StockMovement bulk endpoint qo'shildi ✅

**Yangi endpoint:**
```
POST /api/v1/warehouse/movements/bulk/   — guruhli kirim/chiqim (atomic)
```

**Ishlash tartibi:**
1. Barcha itemlarni validatsiya qil (store ownership, OUT uchun stock yetarliligi)
2. Xato bo'lsa → `ValidationError` → rollback (birortasi ham saqlanmaydi)
3. Hammasi to'g'ri bo'lsa → atomik save

**Yangi serializer lar:**
- `MovementBulkItemSerializer` (fields: product, quantity, unit_cost, supplier)
- `MovementBulkCreateSerializer` (fields: movement_type, branch, warehouse, note, items)

**Refactoring:** `_apply_movement()` helper method ajratildi — `perform_create` va `bulk_create` ikkalasi ishlatadi (AVCO, FIFO, debt_balance mantiq)

**O'zgartirilgan fayllar:**
- `warehouse/serializers.py` — 2 ta yangi serializer
- `warehouse/views.py` — `_apply_movement()` helper + `bulk_create` action
- `warehouse/api_urls.py` — doc comment yangilandi

### 7. postman_test_guide.txt to'liq qayta yozildi ✅

**27 bosqich, 54 qadam** — barcha endpointlar to'g'ri ketma-ketlikda:
Auth → Store → Branch → StoreSettings → Worker → Currency/ExchangeRate → Category → SubCategory → Products → Supplier → Warehouse → Smena → StockMovement (single+bulk) → Stock → StockBatch → Transfer → Wastage → StockAudit → Sale → Customer → SaleReturn → Expense → WorkerKPI → Dashboard → Export/Import → AuditLog → Subscription

---

## 📅 18.03.2026 SESSION #2 — QILINGAN ISHLAR

### 1. Ombor detail ga mahsulotlar ro'yxati qo'shildi ✅

**Muammo:** `GET /api/v1/warehouse/warehouses/{id}/` faqat ombor ma'lumotlarini qaytarardi — ichidagi mahsulotlar ko'rinmasdi.

**Yechim:** `WarehouseDetailSerializer` ga `products` maydoni + yangi `WarehouseStockItemSerializer` qo'shildi.

**O'zgartirilgan fayl:**
- `warehouse/serializers.py` — `WarehouseStockItemSerializer` yangi klass va `WarehouseDetailSerializer.products` SerializerMethodField

**Yangi serializer (`WarehouseStockItemSerializer`) maydonlari:**
- `product_id`, `product_name` — mahsulot identifikatori va nomi
- `quantity` — joriy qoldiq miqdori
- `purchase_price` — o'rtacha tannarx (AVCO, avtomatik)
- `sale_price` — sotish narxi (qo'lda)
- `barcode` — shtrix-kod
- `barcode_image_url` — barcode PNG rasm URL (`/api/v1/warehouse/products/{id}/barcode/`)
- `added_on` — Stock oxirgi yangilangan vaqti

**Endpoint o'zgarishi:**
```
GET /api/v1/warehouse/warehouses/{id}/  — endi "products": [...] qo'shildi
```

**Arxitektura eslatmasi:**
- `purchase_price` = AVCO (o'rtacha tannarx) — StockMovement(IN) da avtomatik yangilanadi
- `sale_price` = sotish narxi — qo'lda o'rnatiladi
- `StockMovement.unit_cost` = faqat shu kirim partiyasining narxi (bir martalik)

---

## 📅 18.03.2026 SESSION — QILINGAN ISHLAR

### 1. Cloudinary media storage integratsiyasi ✅

**Muammo:** Railway har deploy da yangi container yaratadi — `/media/` papkadagi rasmlar yo'qolardi (ephemeral filesystem).

**Yechim:** Cloudinary bulut xizmati ulandi — rasmlar endi `res.cloudinary.com` da saqlanadi.

**O'zgartirilgan fayllar:**
- `config/settings/production.py` — `STORAGES` dict ga Cloudinary backend qo'shildi, `CLOUDINARY_STORAGE` sozlamalari `CLOUDINARY_URL` env dan olinadi
- `config/urls.py` — `DEBUG=True` bo'lganda lokal media fayllar serve qilish qo'shildi
- `requirements/production.txt` — `cloudinary`, `django-cloudinary-storage` paketlari qo'shildi

**Railway env variables:**
- `CLOUDINARY_URL=cloudinary://<api_key>:<api_secret>@<cloud_name>` — yagona format (eng ishonchli)

**Muhim:**
- Faqat **yangi yuklangan** rasmlar Cloudinary ga boradi — eski lokal rasmlar avtomatik ko'chmaydi
- Bepul limit: 25GB/oy
- Rasm URL formati: `https://res.cloudinary.com/<cloud_name>/image/upload/...`

### 2. Loyiha chuqur tahlili — 23 ta muammo topildi, barchasi tuzatildi ✅

**Kritik tuzatishlar:**
- `subscription/serializers.py` — `has_price_list` maydon modeldan o'chirilgan edi, serializer fields dan ham olib tashlandi
- `subscription/utils.py` — `reactivate_downgraded_objects()` da `'branchs'` → `'branches'` plural xato tuzatildi (plural_map qo'shildi)

**Performance (N+1 query) tuzatishlar:**
- `dashboard/utils.py` — `calc_branches()`: har filial uchun alohida query → bitta `values('branch_id').annotate(...)` query
- `dashboard/utils.py` — `calc_current_smena()`: har smena uchun alohida query → bitta `values('smena_id').annotate(...)` query
- `dashboard/utils.py` — `low_stock.count()` sliced queryset da noto'g'ri natija berardi → slicing dan oldin count()

**Race condition tuzatishlar:**
- `expense/views.py` — `ExpenseCategoryViewSet.create()`: `.get(name=...)` o'rniga `serializer.instance` ishlatildi
- `expense/views.py` — `ExpenseViewSet.create()`: `.latest('created_on')` o'rniga `.get(pk=serializer.instance.pk)` ishlatildi

**Config tuzatishlar:**
- `config/settings/base.py` — `CORS_ORIGIN_WHITELIST` → `CORS_ALLOWED_ORIGINS` (django-cors-headers 4.0+ standart)
- `config/cache_utils.py` — ishlatilmagan `import pickle` olib tashlandi
- `accaunt/utils.py` — production da qolgan `print(email)` debug chiqarildi

**Tartib (ordering) tuzatishlar — active birinchi, inactive keyin:**
- `warehouse/views.py` — CategoryViewSet, SubCategoryViewSet, ProductViewSet, WarehouseViewSet, SupplierViewSet → `.order_by('status', 'name')`
- `trade/views.py` — CustomerGroupViewSet → `.order_by('name')`, CustomerViewSet → `.order_by('status', 'name')`
- `store/views.py` — BranchViewSet → `.order_by('status', 'name')`
- `expense/views.py` — ExpenseCategoryViewSet → `.order_by('status', 'name')`

**O'zgartirilgan fayllar (11 ta):**
- `subscription/serializers.py`, `subscription/utils.py`
- `dashboard/utils.py`
- `expense/views.py`
- `config/settings/base.py`, `config/cache_utils.py`
- `accaunt/utils.py`
- `warehouse/views.py`, `trade/views.py`, `store/views.py`
- `project_problems.txt`

**Muhim qoida o'rnatildi:**
- ⚠️ Barcha obyektlar **hard delete** bo'lishi kerak (soft delete emas). Agar soft delete kerak bo'lgan joy bo'lsa — foydalanuvchiga maslahatlashish.

---

## 📅 17.03.2026 SESSION — QILINGAN ISHLAR

### 1. Loyiha to'liq tahlil va tekshiruv ✅

**Maqsad:** Barcha yangi app va ViewSet'larni chuqur ko'rib chiqib, xatolarni aniqlash.

**Topilgan va tuzatilgan kamchiliklar:**

**A) `has_price_list` olib tashlandi** — B12 PriceList rejaldan olib tashlandi (shart emas deb qaror qilindi):
- `subscription/models.py` → `has_price_list = BooleanField(...)` o'chirildi
- `subscription/migrations/0002_remove_subscriptionplan_has_price_list.py` yaratildi

**B) `SubscriptionRequired` permission'lar qo'shildi:**
- `export/views.py` — barcha 10 ta view (5 export + 5 import) ga `SubscriptionRequired('has_export')` qo'shildi
- `dashboard/views.py` — `DashboardView` ga `SubscriptionRequired('has_dashboard')` qo'shildi
- `accaunt/views.py` — `AuditLogViewSet` ga `SubscriptionRequired('has_audit_log')` qo'shildi

**O'zgartirilgan fayllar:**
- `subscription/models.py` — has_price_list o'chirildi (12 ta has_* flag qoldi)
- `subscription/migrations/0002_remove_subscriptionplan_has_price_list.py` — yangi migration
- `export/views.py` — SubscriptionRequired import + barcha 10 permission_classes yangilandi
- `dashboard/views.py` — SubscriptionRequired import + DashboardView permission yangilandi
- `accaunt/views.py` — SubscriptionRequired import + AuditLogViewSet permission yangilandi

**Railway da bajarish kerak:**
```bash
python manage.py migrate subscription   # 0002 migration qo'llash
```

**Hozirgi holat (17.03.2026):**
- V1 to'liq tugallandi ✅ — B12 rejaldan olib tashlandi, barcha qolganlar bajarildi
- Keyingi bosqich: V2 (B11 Telegram, B11.5 SMS, B14 OFD, B18 Offline sync)
- ⚠️ Django admin da `SubscriptionPlan(plan_type='trial')` yaratilishi shart — aks holda Store signal xato beradi

---

## 📅 16.03.2026 SESSION — QILINGAN ISHLAR

### 1. B16 — Export/Import app ✅ (`export` app)

**Yangi fayl:** `export/apps.py`, `export/views.py`, `export/api_urls.py`, `export/utils/__init__.py`

**Export endpointlari (Excel yoki PDF, `?format=excel|pdf`):**
```
GET /api/v1/export/sales/               — Savdolar (date_from, date_to, branch, smena, status)
GET /api/v1/export/expenses/            — Xarajatlar (date_from, date_to, branch, smena, category)
GET /api/v1/export/stocks/              — Qoldiqlar (branch, warehouse)
GET /api/v1/export/stock-movements/     — Kirim/chiqim (date_from, date_to, branch, warehouse, movement_type)
GET /api/v1/export/suppliers/           — Yetkazib beruvchilar (status)
```

**Import endpointlari (Excel yuklash):**
```
GET  /api/v1/export/products/template/          → bo'sh .xlsx shablon
POST /api/v1/export/products/import/            → {created, skipped, errors}
GET  /api/v1/export/customers/template/
POST /api/v1/export/customers/import/
GET  /api/v1/export/stock-movements/template/
POST /api/v1/export/stock-movements/import/
GET  /api/v1/export/suppliers/template/
POST /api/v1/export/suppliers/import/
GET  /api/v1/export/subcategories/template/
POST /api/v1/export/subcategories/import/
```

**Ruxsatlar:** Export → IsAuthenticated; Import → IsManagerOrAbove
**Throttling:** `export` scope — minutiga 5 ta
**Kutubxonalar:** `openpyxl` (Excel), `reportlab` (PDF)
**`store/migrations/0007_storesettings_auto_pdf.py`** — StoreSettings ga `auto_pdf` maydoni

---

### 2. B17 — Dashboard ✅ (`dashboard` app)

**Yangi fayllar:** `dashboard/__init__.py`, `dashboard/apps.py`, `dashboard/utils.py`, `dashboard/views.py`, `dashboard/api_urls.py`

**Endpoint:**
```
GET /api/v1/dashboard/   — To'liq statistika (Redis kesh, 5 daqiqa TTL)
```

**Query parametrlar:**
- `date_from`, `date_to` — YYYY-MM-DD
- `branch` — Branch ID
- `limit` — chart_data uchun nuqtalar soni (default: 30)

**Statistika bloklari (8 ta):**
| Blok | Ma'lumotlar |
|------|-------------|
| `sales` | Bugungi/jami tushum, sotuv soni, o'rtacha chek, o'sish % (oldingi davr bilan) |
| `products` | Jami/faol/kam qoldiq/qoldiqsiz mahsulotlar |
| `customers` | Jami/yangi/qaytib kelgan mijozlar |
| `expenses` | Jami xarajat, kategoriyalar bo'yicha breakdown |
| `suppliers` | Jami yetkazib beruvchi, jami qarz |
| `branches` | Faol filiallar va har birining bugungi savdosi |
| `current_smena` | Joriy smena (agar ochiq bo'lsa): savdo soni, tushum |
| `chart_data` | Kunlik/soatlik savdo grafigi ma'lumotlari |

**Kesh kaliti:** `dashboard_{store_id}_{branch}_{date_from}_{date_to}_{limit}`

---

### 3. B19 — QR Code + AuditLog ✅

**AuditMixin (`accaunt/audit_mixin.py` — yangi fayl):**
- `AuditMixin` klass — barcha ViewSet'larga `_audit_log(action, obj, description, extra_data)` metodi
- Barcha applar ViewSet'lariga qo'shildi: `warehouse`, `trade`, `expense`, `store`
- Eski qo'lda yozilgan `AuditLog.objects.create()` lar `self._audit_log()` bilan almashtirildi

**QR Code (ProductViewSet ga 3 yangi action):**
```
GET  /api/v1/warehouse/products/{id}/qr/       — bitta mahsulot QR PNG rasm
GET  /api/v1/warehouse/products/scan/?code=... — barcode/QR orqali mahsulot qidirish
POST /api/v1/warehouse/products/bulk-qr/       — {product_ids:[...], copies:N} → ZIP
```

**AuditLog endpointlari (`accaunt/api_urls.py` ga qo'shildi):**
```
GET /api/v1/workers/audit-logs/       — ro'yxat (faqat owner)
GET /api/v1/workers/audit-logs/{id}/  — detail
```
Filtrlar: `?model=`, `?action=`, `?worker=`, `?date_from=`, `?date_to=`

**O'zgartirilgan fayllar:**
- `accaunt/audit_mixin.py` — yangi
- `accaunt/serializers.py` — `AuditLogSerializer` qo'shildi
- `accaunt/views.py` — `AuditLogViewSet` qo'shildi
- `accaunt/api_urls.py` — audit-logs router
- `warehouse/views.py` — AuditMixin + QR actions + limit permissions
- `warehouse/api_urls.py` — scan/bulk-qr routelar
- `trade/views.py`, `expense/views.py`, `store/views.py` — AuditMixin

---

### 4. B20 — Subscription tizimi ✅ (`subscription` app)

**Yangi app:** `subscription/` — to'liq yangi app

**Modellar (`subscription/models.py`):**
- `PlanType`: trial | basic | pro | enterprise (Trial = Free)
- `SubscriptionStatus`: trial | active | expired | cancelled
- `SubscriptionPlan`: narx, chegirma, limitlar (max_branches/warehouses/workers/products, 0=cheksiz), 13 ta `has_*` feature flag
- `Subscription`: OneToOne→Store, plan, status, start/end_date, notified_* flaglar, `days_left` property, `is_active` property
- `SubscriptionInvoice`: immutable to'lov yozuvlari
- `SubscriptionDowngradeLog`: `previous_status` saqlanadi (reactivation uchun kritik!)

**`subscription/migrations/0001_initial.py`** — barcha modellar

**Asosiy logika (`subscription/utils.py`):**
- `apply_lifo_deactivation(sub)` — Branch/Warehouse/Worker LIFO inactive (owner hech qachon), select_for_update + atomic
- `reactivate_downgraded_objects(sub)` — DowngradeLog orqali FIFO qaytarish, yangi plan limitiga rioya
- `close_open_smenas(store)` — worker_close=None, "Tizim tomonidan yopildi: obuna cheklovi"
- `_blacklist_worker_tokens(worker)` — simplejwt BlacklistedToken, try/except

**Signals (`subscription/signals.py`):**
- `post_save` Store → Trial subscription avtomatik (`settings.SUBSCRIPTION_TRIAL_DAYS=30`)

**Celery task (`subscription/tasks.py`):**
- `check_subscription_expiry` — har kuni 00:01, notified_10d/3d/1d flaglar, expired → LIFO, smena yopish

**Owner endpointlar:**
```
GET /api/v1/subscription/           — joriy obuna holati
GET /api/v1/subscription/plans/     — barcha tarif rejalari
GET /api/v1/subscription/invoices/  — to'lov tarixi
```

**SuperAdmin endpointlar:**
```
GET    /api/v1/admin/subscriptions/              — ro'yxat (?status=, ?plan_type=)
GET    /api/v1/admin/subscriptions/{id}/         — detail
PATCH  /api/v1/admin/subscriptions/{id}/         — plan/status/sana o'zgartirish
POST   /api/v1/admin/subscriptions/{id}/extend/  — muddat uzaytirish
POST   /api/v1/admin/subscriptions/{id}/add-invoice/ — to'lov qo'shish
```

**`config/cache_utils.py` yangilandi:**
- `get_subscription(store_id)` — 1 soat TTL
- `invalidate_subscription_cache(store_id)`

**`config/settings/base.py` yangilandi:**
- `'subscription'` INSTALLED_APPS ga qo'shildi
- `SUBSCRIPTION_TRIAL_DAYS = 30`
- `SUBSCRIPTION_EXPIRY_NOTIFY = [10, 3, 1]`
- `SUBSCRIPTION_CACHE_TTL = 3600`
- Celery beat: `check-subscription-expiry-daily` (har kuni 00:01)
- `DEFAULT_PERMISSION_CLASSES` ga `ReadOnlyIfExpired` global qo'shildi

**`accaunt/permissions.py` yangilandi:**
- `SubscriptionRequired(feature)` — tarif rejada feature borligini tekshiradi
- `BranchLimitPermission`, `WarehouseLimitPermission`, `WorkerLimitPermission`, `ProductLimitPermission` — create da limit tekshiruvi
- `ReadOnlyIfExpired` — expired do'kon uchun faqat GET + login/logout/subscription yo'llari
- Limit permission'lar qo'shildi: `BranchViewSet`, `WarehouseViewSet`, `WorkerViewSet`, `ProductViewSet`

---

## 📅 13.03.2026 SESSION — QILINGAN ISHLAR

### 1. `barcode_image_url` — ProductDetailSerializer ga qo'shildi ✅
**Fayl:** `warehouse/serializers.py`
- `ProductDetailSerializer` ga `barcode_image_url = SerializerMethodField()` qo'shildi
- `get_barcode_image_url(obj)`: barcode bo'lsa → absolute URL qaytaradi, yo'q bo'lsa → `null`
- URL: `GET /api/v1/warehouse/products/{id}/barcode/` (PNG format, `?format=svg` ham ishlaydi)
- Migration kerak emas

### 2. `postman_test_guide.txt` — Category va SubCategory bo'limlari qo'shildi ✅
**Fayl:** `postman_test_guide.txt`
- 2-BOSQICH: CATEGORY (5 endpoint: list/create/retrieve/update/delete, har biri uchun body, javob, xato holatlari)
- 3-BOSQICH: SUBCATEGORY (5 endpoint + `?category=` filter)
- Eski "2-BOSQICH Products" → 4-BOSQICH ga ko'chirildi
- Test ketma-ketligi [1-17] → [1-20] ga yangilandi, sana 13.03.2026

### 3. Transfer xato matnlari — o'zbekchaga o'zgartirildi ✅
**Fayl:** `warehouse/serializers.py`
- `TransferItemWriteSerializer` bug fix: `queryset=Product.objects.all()` + `validate_product()` metodi
- `from_branch/to_branch/from_warehouse/to_warehouse` uchun o'zbek xato matnlari

### 4. StockListSerializer — `product_id` qo'shildi ✅
**Fayl:** `warehouse/serializers.py`
- `StockListSerializer` ga `product_id = IntegerField(source='product.id')` qo'shildi

### 5. B13 — Supplier (Yetkazib beruvchi) ✅ (`warehouse` app da)

**Yangi modellar (`warehouse/models.py`):**
- `SupplierPaymentType` (TextChoices): cash | card | transfer
- `Supplier` — soft delete, `debt_balance`, `unique_together(store, name)`
- `SupplierPayment` — immutable, to'lov tarixi, yaratilganda `debt_balance` kamayadi
- `StockMovement.supplier` — ixtiyoriy FK (IN harakatda supplier ko'rsatilsa `debt_balance` oshadi)

**`warehouse/migrations/0014_supplier.py`** — Supplier, SupplierPayment, StockMovement.supplier

**Serializers (`warehouse/serializers.py`):**
- `SupplierListSerializer`, `SupplierDetailSerializer`
- `SupplierCreateSerializer` (nom unique validatsiya), `SupplierUpdateSerializer`
- `SupplierPaymentSerializer` (create + list, amount > 0 validatsiya)
- `MovementListSerializer/DetailSerializer` ga `supplier_name` qo'shildi
- `MovementCreateSerializer` ga `supplier` maydoni + `validate_supplier()` qo'shildi

**Views (`warehouse/views.py`):**
- `SupplierViewSet` — CRUD + soft delete, `?status=` filter
- `SupplierPaymentViewSet` — create/list (immutable), `?supplier=`, `?smena=` filter
- `StockMovementViewSet.perform_create()` — IN + supplier → `debt_balance += quantity * unit_cost`

**Admin (`warehouse/admin.py`):**
- `SupplierAdmin` (inline: SupplierPaymentInline), `SupplierPaymentAdmin` (readonly)
- `StockMovementAdmin.list_display` ga `supplier` qo'shildi

**URL (`warehouse/api_urls.py`):**
```
GET  POST   /api/v1/warehouse/suppliers/            (?status=)
GET  PATCH  DELETE /api/v1/warehouse/suppliers/{id}/
GET  POST   /api/v1/warehouse/supplier-payments/    (?supplier=, ?smena=)
```

**Debt logikasi:**
- `StockMovement(IN, supplier=X)` → `debt_balance += quantity * unit_cost`
- `SupplierPayment` yaratilganda → `debt_balance -= amount`

### Rivojlanish rejasi (yangilandi)
- **V1 tartibi:** B15 Celery → B16 Export → B17 Dashboard → B19 QR+AuditLog → B20 Subscription
- **V2 (keyinroq):** B11 Telegram | B11.5 SMS | B14 OFD | B18 Offline sync
- **B12 PriceList** — skip (hozircha `sale_price` yetarli)

---

## 📅 12.03.2026 SESSION — QILINGAN ISHLAR

### 1. Stock by-product endpoint ✅ (`warehouse` app da)
- `warehouse/serializers.py`: `StockLocationSerializer`, `StockByProductSerializer` qo'shildi
- `warehouse/views.py`: `StockViewSet` ga `by_product` action qo'shildi
- `get_serializer_class` da `by_product` uchun `StockByProductSerializer` qaytarish

**Endpoint:**
- `GET /api/v1/warehouse/stocks/by-product/` — mahsulot bo'yicha guruhlangan qoldiqlar

**Javob formati:**
```json
[
  {
    "product_id": 3,
    "product_name": "Pepsi",
    "product_unit": "Kilogram",
    "total_quantity": "190.000",
    "locations": [
      {"stock_id": 6, "location_type": "branch", "location_id": 1, "location_name": "Baraka filial 1", "quantity": "70.000", "updated_on": "2026-03-12 | 10:43"},
      {"stock_id": 5, "location_type": "warehouse", "location_id": 2, "location_name": "2-ombor", "quantity": "120.000", "updated_on": "2026-03-12 | 10:43"}
    ]
  }
]
```

### 2. Rivojlanish rejasi yangilandi
- **V1 tartibi:** B12 PriceList → B13 Supplier → B15 Celery → B16 Export → B17 Dashboard → B19 QR+AuditLog → B20 Subscription
- **V2 (keyinroq):** B11 Telegram | B11.5 SMS | B14 OFD | B18 Offline sync

### 3. #start va #saqla buyruqlari yaratildi
- `.claude/commands/start.md` — sessiya boshlash (5 ta ish)
- `.claude/commands/saqla.md` — sessiya yakunlash (4 ta ish)

---

## 📅 11.03.2026 SESSION — QILINGAN ISHLAR

### 1. AVCO: Product.purchase_price avtomatik yangilanishi ✅
`warehouse/views.py` — `StockMovementViewSet.perform_create()` da StockBatch yaratilgandan KEYIN:
```python
# AVCO: weighted average cost bo'yicha purchase_price yangilanadi
result = StockBatch.objects.filter(product=instance.product, qty_left__gt=0).aggregate(
    total_value=Sum(F('unit_cost') * F('qty_left')), total_qty=Sum('qty_left'))
if result['total_qty']:
    avg = result['total_value'] / result['total_qty']
    Product.objects.filter(pk=instance.product_id).update(purchase_price=avg)
```
`from django.db.models import F, Sum` — Sum qo'shildi.

### 2. B5 — SaleReturn ✅ (`trade` app da)
- `trade/models.py`: `SaleReturnStatus(TextChoices)`, `SaleReturn`, `SaleReturnItem` qo'shildi
- `trade/migrations/0003_salereturn.py`: yangi migration
- `trade/serializers.py`: `SaleReturnItemInputSerializer`, `SaleReturnItemListSerializer`, `SaleReturnListSerializer`, `SaleReturnDetailSerializer`, `SaleReturnCreateSerializer`
- `trade/views.py`: `SaleReturnViewSet` (create/list/retrieve + confirm/cancel actions)
- `trade/api_urls.py`: `router.register('sale-returns', SaleReturnViewSet)` qo'shildi
- `trade/admin.py`: `SaleReturnAdmin`, `SaleReturnItemInline`

**Endpointlar:**
- `POST /api/v1/sale-returns/` — yaratish (status=pending)
- `GET /api/v1/sale-returns/` — ro'yxat (?status, ?branch, ?smena)
- `GET /api/v1/sale-returns/{id}/` — detail
- `PATCH /api/v1/sale-returns/{id}/confirm/` — tasdiqlash (StockMovement(IN) avtomatik)
- `PATCH /api/v1/sale-returns/{id}/cancel/` — bekor qilish

### 3. B6 — expense app ✅
- `expense/models.py`: `ExpenseCategory` (soft delete, unique_together), `Expense` (+receipt_image, +smena)
- `expense/migrations/0001_initial.py`
- `expense/serializers.py`: to'liq CRUD serializers
- `expense/views.py`: `ExpenseCategoryViewSet` (soft delete), `ExpenseViewSet` (hard delete)
- `expense/api_urls.py`: router registrations
- `expense/admin.py`: admin registrations
- `config/urls.py`: `path('api/v1/', include('expense.api_urls'))` qo'shildi

**Endpointlar:**
- `/api/v1/expense-categories/` — CRUD (?status filter)
- `/api/v1/expenses/` — CRUD (?branch, ?category, ?smena, ?date filter)

---

## 📅 10.03.2026 SESSION #2 — MUHOKAMA: Product.purchase_price ARXITEKTURA QARORI

### ✅ BAJARILDI: purchase_price avtomatik yangilanishi (11.03.2026)

**Muammo:**
`Product.purchase_price` qo'lda kiritiladigan maydon — StockMovement (IN) yaratilganda
avtomatik yangilanmaydi. Bu BILLZ, 1C, Odoo kabi barcha tizimlardan farqli.

**Tahlil (o'rganilgan tizimlar):**
| Tizim | purchase_price ma'nosi | Avtomatik yangilanish |
|-------|----------------------|----------------------|
| BILLZ (billz.io) | Oxirgi kirim narxi | ✅ kirimda yangilanadi |
| 1C | Planovaya tsena (reference) | ✅ FIFO/AVCO |
| Odoo | cost (AVCO/FIFO/Standard) | ✅ metod tanlanadi |
| **Bizning tizim** | Default narx (qo'lda) | ❌ HOZIR YANGILANMAYDI |

**Kelishilgan yechim (ertaga amalga oshiriladi):**
`StockMovement (IN)` yaratilganda `Product.purchase_price` AVTOMATIK yangilanadi.

Ikkita variant kelishildi:
- 🔵 **BILLZ usuli** — `purchase_price = oxirgi kirim unit_cost` (oddiy)
- 🟢 **AVCO usuli** — `purchase_price = o'rtacha tannarx` (aniqroq) ← TAVSIYA

```python
# warehouse/views.py — StockMovementViewSet.perform_create() ga qo'shiladi
# AVCO usuli (o'rtacha tannarx):
if instance.movement_type == MovementType.IN and unit_cost is not None:
    # StockBatch yaratilgandan KEYIN average cost hisoblanadi:
    result = (
        StockBatch.objects
        .filter(product=instance.product, qty_left__gt=0)
        .aggregate(
            total_value=Sum(F('unit_cost') * F('qty_left')),
            total_qty=Sum('qty_left')
        )
    )
    if result['total_qty']:
        avg = result['total_value'] / result['total_qty']
        Product.objects.filter(pk=instance.product_id).update(purchase_price=avg)
```

**purchase_price maydoni ma'nosi o'zgarmaydi:**
- Maydon nomi: `purchase_price` (saqlanadi, migration kerak emas)
- Ma'nosi: "O'rtacha tannarx" (AVCO — weighted average cost)
- Read-only: Frontend da ko'rsatiladi, qo'lda o'zgartirilmaydi
- `sale_price`: qo'lda o'rnatiladi (o'zgarmaydi)

---

## 📅 10.03.2026 SESSION — QILINGAN ISHLAR

### 1. Bug fix: StockBatchViewSet permission (`warehouse/views.py`)
```python
# MUAMMO: CanAccess('ombor') — instance edi, DRF class kutardi → TypeError
# TUZATISH:
def get_permissions(self):
    return [IsAuthenticated(), CanAccess('ombor')]
```

### 2. Bug fix: unit_cost=0 StockBatch yaratmaydi (`warehouse/views.py`)
```python
# MUAMMO: if unit_cost and store: → unit_cost=0 da False
# TUZATISH:
if unit_cost is not None and store:
```

### 3. Production hotfix: Railway DB da warehouse_warehouse.is_active yo'q edi
```
migration 0010: ADD COLUMN IF NOT EXISTS is_active/address/created_on (idempotent)
migration 0011: DROP COLUMN IF EXISTS status (eski failed migration qoldig'i, NOT NULL)
migration 0012: is_active → status (ActiveStatus), data migration, SeparateDatabaseAndState
```

### 4. Qoida: Barcha modellarda status=ActiveStatus (is_active emas!)
- `Warehouse.is_active` (BooleanField) → `Warehouse.status` (CharField, ActiveStatus)
- Serializer: `WarehouseCreateSerializer`, `WarehouseUpdateSerializer` yangilandi
- Admin: `list_display`, `list_filter` yangilandi

### 5. Yagona validatsiya xabari qoidasi
Barcha unique nom xatolarida: `"Bunday nomli [X] mavjud. Iltimos boshqa nom tanlang !"`
O'zgartirilgan: Kategoriya, SubKategoriya, Mahsulot, Ombor (2 ta → 1 ta birlashtirildi), Filial, Mijoz guruhi

### 6. StoreSettings: EUR va CNY valyutalari qo'shildi
```python
class DefaultCurrency(models.TextChoices):
    UZS = 'UZS'  # O'zbek so'mi
    USD = 'USD'  # Amerika dollari
    RUB = 'RUB'  # Rossiya rubli
    EUR = 'EUR'  # Yevropa yevrosi  ← YANGI
    CNY = 'CNY'  # Xitoy yuani      ← YANGI
# + show_eur_price, show_cny_price BooleanField lar
# store/migrations/0006_storesettings_eur_cny.py
```

### 7. Postman test qo'llanmasi yaratildi
`postman_test_guide.txt` — 7 bosqich, barcha endpoint, maydonlar, misollar

### 8. #saqla buyrug'i
Keyingi sessionlarda `#saqla` desangiz:
PROJECT_CONTEXT yangilanadi + main branch ga push qilinadi.

---

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

### QOIDA 4 — Barcha modellarda status=ActiveStatus (is_active EMAS!)
```python
# TO'G'RI:
status = models.CharField(max_length=10, choices=ActiveStatus.choices, default=ActiveStatus.ACTIVE)
# NOTO'G'RI:
is_active = models.BooleanField(default=True)  # ← HECH QACHON ISHLATMA
```
**Sabab:** Loyiha bo'yi bir xil qoida. Status filter, admin, serializer hammasida bir xil.

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

## LOYIHA HOLATI (16.03.2026)

| App         | Holat             | Izoh                                                   |
|-------------|-------------------|--------------------------------------------------------|
| `accaunt`   | ✅ Tugallangan    | CustomUser, Worker, AuditLog+AuditLogSerializer+AuditLogViewSet, AuditMixin, JWT auth, WorkerKPI, WorkerLimitPermission, ReadOnlyIfExpired, BranchLimitPermission, WarehouseLimitPermission, ProductLimitPermission, SubscriptionRequired |
| `store`     | ✅ Tugallangan    | Store, Branch(+BranchLimitPermission), StoreSettings(+auto_pdf migration 0007), Smena(X/Z-report) |
| `warehouse` | ✅ Tugallangan    | Category, SubCategory, Product(+QR+scan+bulk_qr+ProductLimitPermission), Currency, ExchangeRate, Warehouse(+WarehouseLimitPermission), Stock, StockMovement, Transfer, StockBatch(FIFO), WastageRecord, StockAudit, Supplier+SupplierPayment |
| `trade`     | ✅ Tugallangan    | Sale, SaleItem, SaleReturn, CustomerGroup, Customer — AuditMixin ulangan |
| `expense`   | ✅ Tugallangan    | ExpenseCategory, Expense — AuditMixin ulangan |
| `export`    | ✅ Tugallangan    | **BOSQICH 16** — Excel/PDF export (Sales/Expenses/Stocks/StockMovements/Suppliers) + Excel import (Products/Customers/StockMovements/Suppliers/SubCategories) |
| `dashboard` | ✅ Tugallangan    | **BOSQICH 17** — 8 blok statistika, Redis 5 daqiqa kesh, branch/date/limit filtrlar |
| `subscription` | ✅ Tugallangan | **BOSQICH 20** — Trial/Basic/Pro/Enterprise rejalari, LIFO deactivation, DowngradeLog, ReadOnlyIfExpired, Celery daily check, SuperAdmin CRUD |
| `StoreSettings` | ✅ Tugallangan | BOSQICH 2 ✅ — 10 guruh, 30+ maydon, signal+Redis kesh |
| `Smena`     | ✅ Tugallangan   | BOSQICH 3 ✅ — SmenaStatus+Smena model, SmenaViewSet (open/close/x-report), migration 0005 |
| `SaleReturn` | ✅ Tugallangan  | BOSQICH 5 ✅ — trade app da, migration 0003             |
| `WastageRecord` | ✅ Tugallangan | BOSQICH 7 — warehouse app da                        |
| `StockAudit` | ✅ Tugallangan | BOSQICH 8 — warehouse app da                           |
| `WorkerKPI` | ✅ Tugallangan  | BOSQICH 9 — accaunt app da                             |
| `Z/X-report` | ✅ Tugallangan | BOSQICH 10 — store app da                              |
| `PriceList` | ⏭ Skip         | BOSQICH 12 — hozircha sale_price yetarli               |
| `Supplier`  | ✅ Tugallangan  | BOSQICH 13 — warehouse app da (debt_balance + to'lov tarixi) |
| `Celery Tasks` | ✅ Tugallangan | BOSQICH 15 — check_low_stock (6 soat), generate_monthly_worker_kpi (oylik), low-stock endpoint |
| `Export`    | 🔄 Rejalashtirilgan | BOSQICH 16 — openpyxl+reportlab o'rnatildi, keyingi sessiyada Excel/PDF implementatsiya |
| `Telegram bot` | ❌ Boshlanmagan | BOSQICH 11 — V2, keyingi versiya                   |
| `SMS xabar`  | ❌ Boshlanmagan  | BOSQICH 11.5 — V2, Eskiz/PlayMobile API              |
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
| `WorkerSelfUpdateSerializer`| PATCH /workers/me/ — email, phone1, phone2, parol (barcha rollar); validate_email/phone1/phone2 + parol tekshiruvi |

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
| GET    | `/workers/me/`    | IsAuthenticated | O'z profilini ko'rish (barcha rollar)                   |
| PATCH  | `/workers/me/`    | IsAuthenticated | email, phone1, phone2, parol yangilash (barcha rollar)  |
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
- **Hard delete**: `instance.delete()` — `status='inactive'` faqat PATCH orqali o'zgartiriladi (o'chirish emas)

### Serializer maydonlari

| Serializer              | Maydonlar                                               |
|-------------------------|---------------------------------------------------------|
| `StoreListSerializer`   | id, name, phone, status, status_display, branch_count   |
| `StoreDetailSerializer` | id, name, address, phone, status, status_display, created_on, **branches**, **workers** |
| `StoreCreateSerializer` | name, address, phone                                    |
| `StoreUpdateSerializer` | name, address, phone, **status**                        |
| `BranchListSerializer`  | id, name, **address**, store_name, phone, status, status_display, **workers_count** |
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
| 0004      | StoreSettings (10 guruh, 30+ maydon)                |
| 0005      | Smena modeli                                        |
| 0006      | StoreSettings: EUR+CNY valyutalari, show_eur_price, show_cny_price ← 10.03.2026 |

### Endpointlar
| Method | URL                   | Ruxsat                        | Izoh                   |
|--------|-----------------------|-------------------------------|------------------------|
| GET    | `/api/v1/stores/`     | IsAuthenticated + CanAccess('dokonlar') | Ro'yxat (branch_count) |
| POST   | `/api/v1/stores/`     | IsOwner                       | Yaratish               |
| GET    | `/api/v1/stores/{id}/`| IsAuthenticated + CanAccess('dokonlar') | Detail (branches+workers) |
| PATCH  | `/api/v1/stores/{id}/`| IsOwner                       | Yangilash (+ status)   |
| DELETE | `/api/v1/stores/{id}/`| IsOwner                       | Hard delete            |
| GET    | `/api/v1/branches/`   | IsAuthenticated               | Ro'yxat                |
| POST   | `/api/v1/branches/`   | IsOwner                       | Yaratish               |
| GET    | `/api/v1/branches/{id}/`| IsAuthenticated             | Detail (workers)       |
| PATCH  | `/api/v1/branches/{id}/`| IsOwner                     | Yangilash (+ status)   |
| DELETE | `/api/v1/branches/{id}/`| IsOwner                     | Hard delete            |

---

## WAREHOUSE APP — TUZILMA (to'liq, 10.03.2026 yangilandi)

### Modellar (haqiqiy)
| Model           | Maydonlar                                                                 | Constraint |
|-----------------|---------------------------------------------------------------------------|------------|
| `Category`      | name, description, store(FK), status, created_on                          | `unique_together = [('store','name')]` |
| `SubCategory`   | name, description, category(FK), store(FK), status, created_on            | `unique_together = [('store','category','name')]` |
| `Currency`      | code, name, symbol, is_base — **store YO'Q, global**                      | `unique: code` |
| `ExchangeRate`  | currency(FK), rate, date, created_on — **store YO'Q, global**             | `unique_together = [('currency','date')]` |
| `Product`       | name, category(FK,null), subcategory(FK,null), unit, purchase_price, sale_price, price_currency(FK,null), barcode(null), image(null), store(FK), status, created_on | `unique_together = [('store','name'),('store','barcode')]` |
| `Warehouse`     | name, address, store(FK), **status**(ActiveStatus, default='active'), created_on | `unique_together = [('store','name')]` |
| `Stock`         | product(FK), branch(FK,null), warehouse(FK,null), quantity, updated_on    | XOR constraint: branch IS NOT NULL xor warehouse IS NOT NULL |
| `StockMovement` | product(FK), branch(FK,null), warehouse(FK,null), movement_type, quantity, unit_cost(null), note, worker(FK,null), created_on | immutable log, XOR |
| `Transfer`      | from_branch/from_warehouse (XOR), to_branch/to_warehouse (XOR), store(FK), worker(FK,null), status(pending\|confirmed\|cancelled), note, confirmed_at(null) | — |
| `TransferItem`  | transfer(FK), product(FK), quantity                                       | — |
| `StockBatch`    | product(FK), location_type(branch\|warehouse), branch(FK,null), warehouse(FK,null), batch_code, unit_cost, qty_left, created_on | FIFO partiya |

⚠️ `Currency` va `ExchangeRate` da `store` maydoni **yo'q** — ular global.
⚠️ `Warehouse` — endi `status` CharField (ActiveStatus) ishlatadi — boshqa modellar bilan bir xil qoida.
⚠️ **Delete qoidasi (10.03.2026):** Barcha modellar **hard delete** — soft delete yo'q.

### Choices
- `ProductUnit`: dona, kg, g, litr, metr, m2, yashik, qop, quti
- `ActiveStatus`: active, inactive — **Barcha modellarda** (Category, SubCategory, Product, **Warehouse**)
- `MovementType`: in (Kirim), out (Chiqim)
- `TransferStatus`: pending, confirmed, cancelled

### Migratsiyalar (to'g'ri zanjir!)
| Migration | Fayl nomi                          | Izoh                                                    |
|-----------|------------------------------------|---------------------------------------------------------|
| 0001      | 0001_initial.py                    | Dastlabki modellar                                      |
| 0002      | 0002_alter_product_unique_together | Product unique_together                                 |
| 0003      | 0003_expand_warehouse_models.py    | Kengaytirilgan modellar                                 |
| 0004 (a)  | 0004_product_image.py              | Product.image ImageField (0003 ga bog'liq)              |
| 0004 (b)  | 0004_subcategory.py                | SubCategory + Product.subcategory (**0004_product_image** ga bog'liq ✅) |
| 0005      | 0005_currency_exchangerate.py      | Currency + ExchangeRate + seed data                     |
| 0006      | 0006_warehouse.py                  | Warehouse modeli + Stock/StockMovement XOR (SeparateDatabaseAndState) |
| 0007      | 0007_transfer.py                   | Transfer + TransferItem                                 |
| 0008      | 0008_stockbatch.py                 | StockBatch (FIFO partiya, batch_code, unit_cost)        |
| 0009      | 0009_remove_exchangerate_source.py | ExchangeRate.source maydoni olib tashlandi              |
| 0010      | 0010_fix_warehouse_is_active.py    | Production fix: ADD COLUMN IF NOT EXISTS is_active/address/created_on (Railway DB da yetishmaydi edi) |
| 0011      | 0011_fix_warehouse_drop_status.py  | Production fix: DROP COLUMN IF EXISTS status (eski failed migration qoldig'i, NOT NULL edi) |
| 0012      | 0012_warehouse_status.py           | Warehouse.is_active → status (ActiveStatus). Data migration: TRUE→active, FALSE→inactive. SeparateDatabaseAndState |

⚠️ `0004_subcategory` → `('warehouse', '0004_product_image')` ga bog'liq (0003_product_image emas!)
⚠️ `trade.0001_initial` → `('warehouse', '0005_currency_exchangerate')` ga bog'liq ✅

### Serializer'lar (muhim maydonlar)
| Serializer                    | fields                                          |
|-------------------------------|-------------------------------------------------|
| `CategoryCreateSerializer`    | name, description, status                             |
| `CategoryUpdateSerializer`    | name, description, status                             |
| `SubCategoryCreateSerializer` | name, description, category, status                   |
| `SubCategoryUpdateSerializer` | name, description, category, status                   |
| `WarehouseCreateSerializer`   | name, address, **status** ← 10.03.2026 is_active dan o'zgartirildi |
| `WarehouseUpdateSerializer`   | name, address, **status**                             |

⚠️ `WarehouseCreateSerializer.validate_name` — mavjud bo'lsa (holati farqsiz):
- "Bunday nomli Ombor mavjud. Iltimos boshqa nom tanlang !"

⚠️ **YAGONA VALIDATSIYA XABARI QOIDASI (10.03.2026):**
Barcha unique nom tekshiruvlarida: `"Bunday nomli [X] mavjud. Iltimos boshqa nom tanlang !"`
- Kategoriya, SubKategoriya, Mahsulot, Ombor, Filial, Mijoz guruhi

### Endpointlar
```
GET/POST   /api/v1/warehouse/categories/       + PATCH/DELETE /{id}/
GET/POST   /api/v1/warehouse/subcategories/    + PATCH/DELETE /{id}/  (?category=<id>)
GET/POST   /api/v1/warehouse/currencies/       + PATCH        /{id}/
GET/POST   /api/v1/warehouse/exchange-rates/   + GET          /{id}/  (?currency=USD&date=2026-03-03)
GET/POST   /api/v1/warehouse/products/         + PATCH/DELETE /{id}/  (?category=&subcategory=&status=)
GET        /api/v1/warehouse/products/{id}/barcode/                   (?format=svg)
GET/POST   /api/v1/warehouse/warehouses/       + PATCH/DELETE /{id}/
GET/POST   /api/v1/warehouse/stocks/           + PATCH/DELETE /{id}/
GET/POST   /api/v1/warehouse/movements/        + GET          /{id}/  (immutable)
GET/POST   /api/v1/warehouse/transfers/        + GET          /{id}/
POST       /api/v1/warehouse/transfers/{id}/confirm/
POST       /api/v1/warehouse/transfers/{id}/cancel/
GET        /api/v1/warehouse/batches/          + GET          /{id}/  (?product=<id>, read-only)
```

### Ruxsatlar
- `list/retrieve` → `IsAuthenticated + CanAccess('mahsulotlar')` yoki `CanAccess('ombor')`
- `create/update/destroy` → `IsAuthenticated + IsManagerOrAbove`
- `StockMovement` → faqat `GET` va `POST` (immutable)

### Muhim logika
- **StockMovement POST** → `Stock.quantity` avtomatik yangilanadi (`@transaction.atomic` + `select_for_update()` + `F()`)
- **IN harakatda unit_cost bo'lsa** → `StockBatch` yaratiladi (FIFO)
- **OUT harakatda** → FIFO dan narx hisoblanadi → `unit_cost` saqlashadi
- **Transfer confirm** → `@transaction.atomic`, barcha itemlar tekshiriladi, yetarli bo'lmasa rollback
- **Soft delete YO'Q** — barcha modellar hard delete (`instance.delete()`)
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

### BOSQICH 1.5 — Warehouse (Ombor) modeli ✅ BAJARILDI (05.03.2026)
| # | Vazifa | Holat |
|---|--------|-------|
| 1.5.1 | Warehouse modeli (nom, manzil, **status** (ActiveStatus), store FK) | ✅ Bajarildi (10.03.2026 is_active→status) |
| 1.5.2 | Stock: branch OR warehouse (XOR constraint) | ✅ Bajarildi |
| 1.5.3 | StockMovement: branch OR warehouse (XOR constraint) | ✅ Bajarildi |
| 1.5.4 | WarehouseViewSet: CRUD + hard delete (status — soft delete qoidasi) | ✅ Bajarildi |
| 1.5.5 | StockViewSet, MovementViewSet — branch\|warehouse qo'llab-quvvatlash | ✅ Bajarildi |

**Muhim farq:**
- `Branch` (Filial) → sotuv nuqtasi (kassa, sotuvchi)
- `Warehouse` (Ombor) → faqat saqlash (tovar keladi, filiallarga uzatiladi)
- `Stock` va `StockMovement` → `branch IS NOT NULL, warehouse IS NULL` YOKI `branch IS NULL, warehouse IS NOT NULL`

**Yangi fayllar:**
- `warehouse/migrations/0006_warehouse.py` — Warehouse modeli + Stock/StockMovement yangilash

**Endpointlar:**
```
GET/POST   /api/v1/warehouse/warehouses/
GET/PATCH  /api/v1/warehouse/warehouses/{id}/
DELETE     /api/v1/warehouse/warehouses/{id}/   ← hard delete (instance.delete())
```

---

### BOSQICH 1.6 — Transfer (Tovar ko'chirish) ✅ BAJARILDI (05.03.2026)
| # | Vazifa | Holat |
|---|--------|-------|
| 1.6.1 | Transfer modeli (from/to: branch\|warehouse, status, confirmed_at) | ✅ Bajarildi |
| 1.6.2 | TransferItem modeli (transfer FK, product FK, quantity) | ✅ Bajarildi |
| 1.6.3 | TransferCreateSerializer — guruhlab, from XOR, to XOR, items[] | ✅ Bajarildi |
| 1.6.4 | TransferViewSet.confirm() — @transaction.atomic, select_for_update, F() | ✅ Bajarildi |
| 1.6.5 | TransferViewSet.cancel() — faqat pending dan | ✅ Bajarildi |

**Yo'nalishlar (barchasi qo'llab-quvvatlanadi):**
```
Ombor  → Filial    (eng ko'p)
Filial → Ombor     (qaytarish)
Ombor  → Ombor     (ichki ko'chirish)
Filial → Filial    (filiallar o'rtasida)
```

**Holatlari:**
```
pending   → yaratilgan, Stock O'ZGARMAYDI. Xato bo'lsa cancel qilish mumkin.
confirmed → tasdiqlangan. Stock yangilangan. IMMUTABLE.
cancelled → bekor qilingan. Stock o'zgarmaydi.
```

**confirm() jarayoni (atomic):**
```
1. status == pending tekshirish
2. Barcha itemlar uchun from_stock LOCK (select_for_update)
3. Qoldiq yetarliligini tekshirish (HAMMASI tekshiriladi)
   → Bitta mahsulot kam bo'lsa → HECH BIRI o'zgarmaydi (rollback)
4. Har bir item uchun:
   StockMovement(OUT) → from joyi
   from Stock - quantity  (F())
   StockMovement(IN)  → to joyi
   to Stock + quantity (get_or_create + F())
5. transfer.status = confirmed, confirmed_at = now()
6. AuditLog (bitta yozuv, jami qty bilan)
```

**Yangi fayllar:**
- `warehouse/migrations/0007_transfer.py` — Transfer + TransferItem modellari

**Endpointlar:**
```
GET/POST   /api/v1/warehouse/transfers/
GET        /api/v1/warehouse/transfers/{id}/
POST       /api/v1/warehouse/transfers/{id}/confirm/
POST       /api/v1/warehouse/transfers/{id}/cancel/
```

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
default_currency      = CharField(max_length=3, choices=DefaultCurrency, default='UZS')  # UZS | USD | RUB | EUR | CNY ← 10.03.2026 EUR+CNY qo'shildi
show_usd_price        = BooleanField(default=False)  # USD narxini ko'rsatish
show_rub_price        = BooleanField(default=False)  # RUB narxini ko'rsatish
show_eur_price        = BooleanField(default=False)  # EUR narxini ko'rsatish ← 10.03.2026 qo'shildi
show_cny_price        = BooleanField(default=False)  # CNY narxini ko'rsatish ← 10.03.2026 qo'shildi

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
               → Hard delete: instance.delete() — status='inactive' faqat PATCH orqali

Sale:          branch(FK), store(FK), worker(FK), customer(FK,null),
               smena(FK,null), payment_type(cash|card|mixed|debt),
               total_price, discount_amount, paid_amount, debt_amount,
               status(completed|cancelled), note, created_on

SaleItem:      sale(FK), product(FK), quantity, unit_price, total_price
               → immutable (o'zgartirilmaydi)
```

**Serializer'lar (9 ta):**
```
CustomerGroupListSerializer
CustomerGroupCreateSerializer  ← validate_name: bir do'konda bir xil nom → 400
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
           → GET /{id}/ da debt_sales: mijozning barcha nasiya sotuvlari ro'yxati
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
  → store app da SmenaViewSet (close action, x_report action)
  → JSON javob (PDF export BOSQICH 16 da qo'shiladi)
  → Endpoint: PATCH /api/v1/shifts/{id}/close/    ← Z-report + smena yopiladi
              GET   /api/v1/shifts/{id}/x-report/ ← X-report (smena yopilmaydi)
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

### BOSQICH 11.5 — SMS xabar yuborish tizimi ← YANGI
```
Dastur nomidan worker yoki ownerlarga SMS yuborish funksiyasi.

Xabar turlari:
  - Smena ochilganda/yopilganda owner ga SMS xabar
  - Kam qoldiq (low_stock) ogohlantirish SMS orqali
  - Kunlik sotuv hisoboti (Celery beat, har kuni 20:00)
  - Yangi xodim qo'shilganda owner ga bildirishnoma

SMS provayderlar (Uzbekiston):
  - Eskiz.uz API (https://eskiz.uz)
  - PlayMobile API (https://playmobile.uz)

StoreSettings ga qo'shiladigan maydonlar:
  sms_enabled      = BooleanField(default=False)
  sms_provider     = CharField(choices=[('eskiz','Eskiz'),('playmobile','PlayMobile')], default='eskiz')
  sms_api_token    = CharField(null=True, blank=True)  ← owner o'z tokenini kiritadi
  sms_notify_owner = BooleanField(default=True)  ← owner ga SMS yuborish

Texnik:
  SMS_DEFAULT_SENDER → env variable (settings.py da)
  httpx.post() orqali API chaqirish
  Barcha SMS lar Celery task orqali (async, queue da)
  SmsLog modeli — yuborilgan SMS lar tarixi (phone, message, status, sent_at)
  → requirements/base.txt ga httpx qo'shiladi (agar hali bo'lmasa)
```

---

### BOSQICH 12 — PriceList (Narx ro'yxati) ← YANGI
```
CustomerGroup (trade app da) — BOSQICH 4 da allaqachon bor:
  name, store(FK), discount(%), created_on

⚠️ Customer.group(FK, null) → CustomerGroup bog'lanishi BOSQICH 4 da qo'shilgan.
   BOSQICH 12 da faqat PriceList modeli va logikasi qo'shiladi.

PriceList (trade app da) — YANGI:
  product(FK), customer_group(FK), price
  store(FK), valid_from, valid_to(null)

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

### BOSQICH 20 — Subscription (Obuna tizimi) ← YANGI

**Yangi app:** `subscription`

#### SubscriptionStatus (TextChoices)
```python
TRIAL     = 'trial'      # 30 kunlik bepul sinov — yangi akkaunt ochilganda
ACTIVE    = 'active'     # To'langan yoki kupon orqali faol
EXPIRED   = 'expired'    # Muddati tugagan → tizimga kirish bloklanadi
CANCELLED = 'cancelled'  # Bekor qilingan
```

#### BillingCycle (TextChoices)
```python
MONTHLY = 'monthly'  # Oylik to'lov
YEARLY  = 'yearly'   # Yillik to'lov
```

#### Model 1 — SubscriptionPlan (admin boshqaradi)
```
name           CharField(unique)     'basic' | 'normal' | 'pro'
display_name   CharField             'Basic' | 'Normal' | 'Pro'
max_branches   IntegerField(null)    null = cheksiz
max_warehouses IntegerField(null)    null = cheksiz
max_workers    IntegerField(null)    null = cheksiz
monthly_price  DecimalField          Oylik narx (UZS)
yearly_price   DecimalField          Yillik narx (UZS)
is_active      BooleanField          Plan sotuvda bormi
order          IntegerField          Ko'rsatish tartibi (1=Basic, 2=Normal, 3=Pro)

Seed data (migration da):
  Basic:  max_branches=1, max_warehouses=1, max_workers=4
  Normal: max_branches=3, max_warehouses=3, max_workers=10
  Pro:    max_branches=null, max_warehouses=null, max_workers=null
```

#### Model 2 — Subscription (har do'kon uchun bitta, OneToOne → Store)
```
store           OneToOneField(Store)          related_name='subscription'
plan            FK(SubscriptionPlan, null)    null = trial davri
status          CharField                     SubscriptionStatus
billing_cycle   CharField(null)               BillingCycle
start_date      DateField
end_date        DateField                     Qachon tugaydi
is_trial        BooleanField(default=True)
notified_3_days BooleanField(default=False)   3 kunlik eslatma yuborilganmi
notified_1_day  BooleanField(default=False)   1 kunlik eslatma yuborilganmi
created_on      DateTimeField(auto_now_add)
```

#### Model 3 — Coupon (admin yaratadi)
```
code          CharField(unique)         'PROMO2026', 'SUMMER50'
plan          FK(SubscriptionPlan,null) null = barcha planlarga; aks holda SHART O'SHA PLAN
duration_days IntegerField              Necha kunlik bepul kirish beradi
max_uses      IntegerField(null)        null = cheksiz; masalan 100 ta do'kon
used_count    IntegerField(default=0)   Necha kishi ishlatgan (avtomatik ++)
valid_from    DateField                 Kupon qachondan amal qiladi
valid_to      DateField(null)           null = muddatsiz
is_active     BooleanField(default=True)
created_on    DateTimeField(auto_now_add)

Kupon ishlash logikasi:
  - plan belgilangan bo'lsa → do'kon O'SHA PLAN ga duration_days kunlik bepul kirish oladi
  - plan=null bo'lsa → joriy plan uzaytiriladi (duration_days kun)
  - Bir do'kon bir kuponi faqat bir marta ishlatadi (CouponUsage unique_together)
  - max_uses to'lsa → kupon ishlamaydi (400 xato)
  - valid_to o'tgan bo'lsa → ishlamaydi (400 xato)
  - is_active=False bo'lsa → ishlamaydi (400 xato)
```

#### Model 4 — CouponUsage (kim ishlatganini kuzatadi)
```
coupon          FK(Coupon)
store           FK(Store)
used_at         DateTimeField(auto_now_add)
extended_until  DateField              Obuna qachongacha uzaygani

unique_together = [('coupon', 'store')]  ← bir do'kon bir kuponi 1 marta
```

#### Model 5 — SubscriptionPayment (to'lovlar tarixi)
```
subscription   FK(Subscription)           related_name='payments'
plan           FK(SubscriptionPlan)        Qaysi plan uchun to'langan
billing_cycle  CharField                  monthly | yearly
amount         DecimalField               To'langan summa (UZS)
coupon         FK(Coupon, null)            Kupon ishlatilganmi
status         CharField                  completed | pending | failed
paid_at        DateTimeField              To'lov vaqti
note           TextField(blank)           Admin izohi (masalan: "Payme orqali")
created_by     FK(CustomUser, null)       Admin tomonidan yozilsa

→ Do'kon egasi faqat o'z to'lovlarini ko'ra oladi
→ Admin barcha to'lovlarni ko'radi va qo'sha oladi
→ V2 da: Payme/Click gateway orqali avtomatik to'ldiriladi
```

#### Signal
```python
# Store yaratilganda AVTOMATIK trial Subscription yaratiladi
@receiver(post_save, sender=Store)
def create_trial_subscription(sender, instance, created, **kwargs):
    if created:
        Subscription.objects.create(
            store=instance,
            plan=None,
            status='trial',
            is_trial=True,
            start_date=today,
            end_date=today + timedelta(days=30),
        )
# Sabab: hech qachon "subscription topilmadi" xatosi bo'lmasin
```

#### Middleware — Har so'rovda obuna tekshiruvi
```python
class SubscriptionMiddleware:
    # Bu yo'llarga tekshiruv qo'llanilmaydi:
    EXEMPT_PREFIXES = [
        '/api/v1/auth/',
        '/api/v1/subscription/',
        '/health/',
        '/admin/',
        '/swagger/',
    ]

    def __call__(self, request):
        # Faqat authenticated request lar tekshiriladi
        # Superuser/admin bypass qiladi
        # Subscription.status == 'expired' bo'lsa → 403
        # {"detail": "Obuna muddati tugagan. Yangilash uchun /api/v1/subscription/"}
```

#### Cheklovlar (Enforcement) — Branch va Worker yaratishda
```python
# Branch yaratishda (store/views.py BranchViewSet.perform_create):
sub = worker.store.subscription
if sub.status == 'expired':
    raise PermissionDenied("Obuna muddati tugagan.")
plan = sub.plan
if plan and plan.max_branches is not None:
    active_count = Branch.objects.filter(store=worker.store, status='active').count()
    if active_count >= plan.max_branches:
        raise PermissionDenied(f"'{plan.display_name}' tarifi faqat {plan.max_branches} ta filialga ruxsat beradi.")

# Worker yaratishda (accaunt/views.py WorkerViewSet.perform_create):
if plan and plan.max_workers is not None:
    active_count = Worker.objects.filter(store=worker.store).exclude(status='ishdan_ketgan').count()
    if active_count >= plan.max_workers:
        raise PermissionDenied(f"'{plan.display_name}' tarifi faqat {plan.max_workers} ta xodimga ruxsat beradi.")

# Pro plan (null limit) → tekshiruv o'tkazilmaydi
```

#### Celery Task — Kunlik eslatma va muddatni tekshirish (har kuni 08:00)
```python
@shared_task
def check_subscription_expirations():
    today = timezone.now().date()

    # 3 kun qolganda (va eslatma yuborilmagan)
    subs_3days = Subscription.objects.filter(
        status='active', end_date=today + timedelta(days=3), notified_3_days=False
    )
    for sub in subs_3days:
        # → Telegram xabar (agar telegram_enabled)
        # → Email xabar (ixtiyoriy)
        sub.notified_3_days = True
        sub.save(update_fields=['notified_3_days'])

    # 1 kun qolganda
    subs_1day = Subscription.objects.filter(
        status='active', end_date=today + timedelta(days=1), notified_1_day=False
    )
    for sub in subs_1day:
        sub.notified_1_day = True
        sub.save(update_fields=['notified_1_day'])

    # Muddati o'tganlar → expired ga o'tkazish
    expired = Subscription.objects.filter(
        status__in=['trial', 'active'], end_date__lt=today
    )
    expired.update(status='expired')
```

#### API Endpointlar

**Do'kon egasi uchun (IsOwner):**
```
GET  /api/v1/subscription/               → O'z obunasi, qancha vaqt qolgan, joriy plan
GET  /api/v1/subscription/plans/         → Barcha faol planlar va narxlari (ro'yxat)
POST /api/v1/subscription/activate-coupon/ → {"code": "PROMO2026"} → obunani faollashtiradi
GET  /api/v1/subscription/payments/      → O'z to'lovlari tarixi (faqat o'zini ko'radi)
```

**Admin uchun (IsAdminUser — Django superuser):**
```
# Tarif planlari (CRUD)
GET/POST      /api/v1/admin/plans/          → Plan yaratish, ro'yxat
PATCH/DELETE  /api/v1/admin/plans/{id}/     → Plan tahrirlash, o'chirish

# Kuponlar (CRUD)
GET/POST      /api/v1/admin/coupons/        → Kupon yaratish, ro'yxat
PATCH/DELETE  /api/v1/admin/coupons/{id}/   → Kupon tahrirlash, o'chirish
GET           /api/v1/admin/coupons/{id}/usages/ → Kim ishlatganini ko'rish

# Barcha obunalar (monitoring)
GET           /api/v1/admin/subscriptions/              → Barcha do'konlar obunasi
              ?status=trial|active|expired|cancelled
              ?plan=basic|normal|pro
GET           /api/v1/admin/subscriptions/{id}/         → Bitta obuna detayli
POST          /api/v1/admin/subscriptions/{id}/extend/  → Qo'lda uzaytirish
              {"days": 30, "note": "Bonus"}

# To'lovlar (CRUD + monitoring)
GET/POST      /api/v1/admin/payments/        → Barcha to'lovlar, yangi to'lov qo'shish
PATCH         /api/v1/admin/payments/{id}/   → To'lov tahrirlash

# Moliyaviy dashboard (admin uchun)
GET           /api/v1/admin/financial/
  Javob:
  {
    "total_revenue": {"monthly": 0, "yearly": 0, "total": 0},
    "subscriptions_by_status": {"trial": 0, "active": 0, "expired": 0},
    "subscriptions_by_plan":   {"basic": 0, "normal": 0, "pro": 0},
    "revenue_by_month": [{"month": "2026-03", "amount": 0}, ...],  # oxirgi 12 oy
    "coupon_stats": {"total_coupons": 0, "total_uses": 0, "active_coupons": 0},
    "expiring_soon": 0   # keyingi 7 kun ichida tugaydigan obunalar soni
  }
```

#### Ruxsatlar jadvali
```
                              Do'kon egasi    Admin (superuser)
GET /subscription/            ✅ O'zini        ✅ Barcha
GET /subscription/plans/      ✅              ✅
POST /activate-coupon/        ✅              ✅
GET /subscription/payments/   ✅ Faqat o'zi   ✅ Barcha
/admin/plans/*                ❌              ✅
/admin/coupons/*              ❌              ✅
/admin/subscriptions/*        ❌              ✅
/admin/payments/*             ❌              ✅
/admin/financial/             ❌              ✅
```

#### Yangi fayllar
```
subscription/
├── __init__.py
├── apps.py
├── models.py        ← SubscriptionPlan, Subscription, Coupon, CouponUsage, SubscriptionPayment
├── serializers.py   ← barcha serializerlar
├── views.py         ← do'kon egasi + admin ViewSet lar
├── admin.py         ← Django admin panel
├── permissions.py   ← IsAdminUser permission
├── middleware.py    ← SubscriptionMiddleware
├── signals.py       ← Store → auto trial Subscription
├── tasks.py         ← check_subscription_expirations (Celery)
└── migrations/
    └── 0001_initial.py  ← barcha modellar + seed data (Basic/Normal/Pro planlar)
```

#### Yangilangan fayllar
```
store/signals.py      ← create_trial_subscription signal qo'shiladi
config/celery.py      ← check_subscription_expirations Celery beat task qo'shiladi (har kuni 08:00)
config/settings/base.py ← INSTALLED_APPS ga 'subscription' qo'shiladi
config/middleware.py yoki config/settings/base.py ← MIDDLEWARE ga SubscriptionMiddleware qo'shiladi
config/urls.py        ← /api/v1/ va /api/v1/admin/ urllar qo'shiladi
```

#### Muhim eslatmalar
```
⚠️ Trial davri: yangi Store ochilganda AVTOMATIK 30 kunlik trial yaratiladi (signal orqali)
⚠️ Pro plan: max_* = null → barcha cheklovlar bypass qilinadi (tekshiruv o'tkazilmaydi)
⚠️ Kupon + plan: kupon plan belgilagan bo'lsa, do'kon O'SHA PLAN ga o'tadi (yuqoriga ham, pastga ham)
⚠️ To'lov integratsiyasi (Payme/Click) → V2 da, hozir admin qo'lda SubscriptionPayment yozadi
⚠️ Eslatma kanali: Telegram (StoreSettings.telegram_enabled=True bo'lsa), aks holda faqat log
⚠️ Admin bypass: Django superuser (is_superuser=True) SubscriptionMiddleware ni chetlab o'tadi
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
20 ❌     Subscription (Obuna tizimi)      ← YANGI

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

## QILINGAN ISHLAR (07.03.2026)

### Git log (so'nggi commitlar, 07.03.2026)
```
24460eb  fix(warehouse): migration 0006 — step 5/6/8 to'liq idempotent (branch_id yo'q holat va noto'g'ri data uchun)
ad767d2  fix(warehouse): migration 0006 — SeparateDatabaseAndState + RunSQL IF NOT EXISTS (idempotent) Railway PostgreSQL uchun
b9e0a30  chore: add .dockerignore, untrack db.sqlite3 va .pyc fayllar
ce9d69e  tushunmovchilik tuzatildi
a476f10  tushunmovchilik tuzatildi
268de04  fix(warehouse): migration 0006 — barcha operatsiyalar idempotent qilindi
c926112  fix(warehouse): migration 0006 — CreateModel Warehouse idempotent qilindi
8c77ec7  add
d019d95  Merge branch 'claude/objective-aryabhata': BOSQICH 1.7 — FIFO StockBatch
768456b  feat(warehouse): BOSQICH 1.7 — FIFO StockBatch (partiyali ombor hisob-kitob)
```

### Qo'shilgan xususiyatlar (07.03.2026)
| Xususiyat | Joyi | Izoh |
|-----------|------|------|
| `.dockerignore` | root | `myenv/`, `.git/`, `__pycache__/`, `db.sqlite3`, `.claude/` Docker image dan chiqarildi. Build vaqti: **41s → 14s** |
| `db.sqlite3` untrack | `.gitignore` allaqachon bor edi | `git rm --cached db.sqlite3` — production PostgreSQL ishlatadi, git da keraksiz |
| 39 ta `.pyc` fayl untrack | barcha applar | Tasodifan commit qilingan bytecode fayllar tozalandi |

### Topilgan va tuzatilgan muammolar (07.03.2026)

#### 1. `0006_warehouse.py` — Railway PostgreSQL deploy muammosi (TUZATILDI)
**Muammo zanjiri:**
1. `d019d95` merge → `0006_warehouse.py` `SeparateDatabaseAndState + RunPython` ishlatardi
   - Local SQLite: `LookupError` (apps.get_model from_state da Warehouse yo'q)
   - Railway PostgreSQL: `pg_constraint` query ishlaydi, lekin...
2. `268de04` commit ("idempotent qilindi") — Railway PostgreSQL da:
   - `warehouse_warehouse` jadvalini yaratdi (**django_migrations ga yozilmadi** — atomic bo'lmagan `cursor.execute()`)
   - `warehouse_stockmovement.branch_id` kolumnasini **o'chirib yubordi** (sababı noma'lum, ehtimol DROP + qayta yaratishda xato)
3. `a476f10` — oddiy `CreateModel` → `"relation warehouse_warehouse already exists"` xatosi
4. `b9e0a30` — `.dockerignore` qo'shildi → build tezlashdi, lekin migrate hali xato
5. `ad767d2` — `SeparateDatabaseAndState + RunSQL IF NOT EXISTS` → `"column branch_id does not exist"` xatosi (stockmovement da)
6. **`24460eb` — TO'LIQ YECHIM** (push qilindi, Railway natijasi kutilmoqda):
   - Step 6 (`stockmovement.branch_id`): `DO $$ IF EXISTS → DROP NOT NULL; ELSE → ADD COLUMN $$`
   - Step 5, 8 (XOR constraint): `DECLARE invalid_rows; SELECT COUNT(*) → IF 0 THEN ADD CONSTRAINT ELSE RAISE WARNING`

**Hozirgi `warehouse/migrations/0006_warehouse.py` tuzilmasi:**
```python
migrations.SeparateDatabaseAndState(
    state_operations=[...],   # 8 ta standart Django op (CreateModel, AlterField, AddField, ...)
    database_operations=[     # 8 ta RunSQL (IF NOT EXISTS, DO $$ ... $$)
        RunSQL("CREATE TABLE IF NOT EXISTS warehouse_warehouse ..."),
        RunSQL("ALTER TABLE warehouse_stock ALTER COLUMN branch_id DROP NOT NULL"),
        RunSQL("ALTER TABLE warehouse_stock ADD COLUMN IF NOT EXISTS warehouse_id ..."),
        RunSQL("CREATE UNIQUE INDEX IF NOT EXISTS ... ON warehouse_stock(product_id, warehouse_id)"),
        RunSQL("DO $$ ... stock_branch_xor_warehouse (data check bilan) ...$$"),
        RunSQL("DO $$ IF branch_id EXISTS: DROP NOT NULL; ELSE: ADD COLUMN $$"),  # KEY FIX
        RunSQL("ALTER TABLE warehouse_stockmovement ADD COLUMN IF NOT EXISTS warehouse_id ..."),
        RunSQL("DO $$ ... movement_branch_xor_warehouse (data check bilan) ... $$"),
    ]
)
```

#### 2. MIXED payment validatsiya bagi (HALI TUZATILMAGAN)
- **Joyi**: `trade/views.py:533-538`
- **Muammo**: `PaymentType.MIXED` uchun `paid_amount > net_price` tekshiriladi, lekin `paid_amount != net_price` tekshirilmaydi
- **FIX kerak**: `if paid_amount > net_price:` → `if paid_amount != net_price:`

#### 3. N+1 query muammo (HALI TUZATILMAGAN)
- **Joyi**: `store/serializers.py:58`
- **Muammo**: `obj.workers.count()` — prefetch_related cacheni ishlatmaydi
- **FIX kerak**: `len([w for w in obj.workers.all() if w.status in ('active', 'tatil')])`

---

## LOYIHA TUZILMASI (07.03.2026)

```
shop_crm_system/
├── .dockerignore         ← ✅ YANGI (b9e0a30) — myenv/, .git/, __pycache__/, db.sqlite3 chiqarildi
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
├── store/                ✅ Store, Branch, StoreSettings (soft delete, multi-tenant)
│   ├── models.py         ← Store, Branch, StoreStatus, StoreSettings (10 guruh, 30+ maydon)
│   ├── views.py          ← StoreViewSet, BranchViewSet, StoreSettingsViewSet
│   ├── serializers.py    ← workers detail, BranchListSerializer (workers_count — N+1 bug bor!)
│   ├── api_urls.py       ← /api/v1/stores/, /api/v1/branches/, /api/v1/settings/
│   ├── signals.py        ← ✅ QOIDA 1 (auto StoreSettings yaratish)
│   └── migrations/
│       ├── 0003_alter_branch_unique_together.py
│       ├── 0004_storesettings.py
│       └── 0005_smena.py
├── warehouse/            ✅ BOSQICH 1–1.7 (Category, SubCategory, Product, Currency,
│   │                        ExchangeRate, Warehouse, Stock, StockMovement, Transfer,
│   │                        TransferItem, StockBatch)
│   ├── models.py
│   ├── views.py          ← 10 ta ViewSet
│   ├── serializers.py
│   ├── api_urls.py       ← /api/v1/warehouse/ (10 router)
│   ├── tasks.py          ← Celery: valyuta kursi yangilash (har kuni 9:00)
│   └── migrations/
│       ├── 0001_initial.py
│       ├── 0002_alter_product_unique_together.py
│       ├── 0003_expand_warehouse_models.py  ← intentionally empty
│       ├── 0004_product_image.py
│       ├── 0004_subcategory.py
│       ├── 0005_currency_exchangerate.py
│       ├── 0006_warehouse.py  ← ⚠️ SeparateDatabaseAndState+RunSQL (idempotent, Railway fix)
│       ├── 0007_transfer.py
│       └── 0008_stockbatch.py
├── trade/                ✅ BOSQICH 4 (CustomerGroup, Customer, Sale, SaleItem, Smena)
│   ├── models.py         ← PaymentType(CASH/CARD/DEBT/MIXED), Sale, SaleItem, CustomerGroup, Customer
│   ├── views.py          ← SaleViewSet (13-qadam + FIFO), SmenaViewSet (open/close/x-report)
│   │                     ← ⚠️ MIXED payment bug: paid_amount != net_price tekshirilmaydi (line 533)
│   ├── serializers.py
│   ├── api_urls.py       ← /api/v1/sales/, /api/v1/customers/, /api/v1/shifts/, ...
│   └── migrations/
│       ├── 0001_initial.py
│       └── 0002_saleitem_unit_cost.py
├── expense/              ❌ Hali boshlanmagan (BOSQICH 6)
├── requirements/
│   ├── base.txt
│   └── production.txt    ← gunicorn, whitenoise, dj-database-url, psycopg2
├── requirements.txt      ← -r requirements/production.txt
├── Dockerfile            ← python:3.12-slim, collectstatic BUILD vaqtida, appuser
├── entrypoint.sh         ← set -e; migrate; gunicorn (PORT env)
└── railway.toml          ← builder=DOCKERFILE, healthcheckPath=/health/, timeout=300
```


---

## POSTMAN TEST QO'LLANMASI

============================================================
  SHOP CRM SYSTEM — POSTMAN TEST QO'LLANMASI
  Base URL: https://shopcrmsystem-production.up.railway.app/api/v1
  Header:   Authorization: Bearer <access_token>
  Sana: 19.03.2026  |  Jami: 90+ endpoint
============================================================

TO'G'RI TEST KETMA-KETLIGI (umumiy):
  [1]  Auth — ro'yxatdan o'tish, login
  [2]  Store — do'kon ma'lumotlari
  [3]  Branch — filiallar
  [4]  StoreSettings — sozlamalar
  [5]  Worker — xodimlar
  [6]  Currency + ExchangeRate — valyutalar
  [7]  Category → SubCategory → Product
  [8]  Supplier — yetkazib beruvchilar
  [9]  Warehouse — omborlar
  [10] Smena ochish
  [11] StockMovement IN — kirim (yoki bulk)
  [12] Stocks — qoldiqlarni tekshirish
  [13] StockBatch — FIFO partiyalar
  [14] Transfer
  [15] Wastage — isrof
  [16] StockAudit — inventarizatsiya
  [17] Sale — sotuv
  [18] SaleReturn — qaytarish
  [19] Expense — xarajat
  [20] Smena yopish → Z-Report
  [21] Dashboard
  [22] Export / Import
  [23] WorkerKPI
  [24] AuditLog
  [25] Subscription


============================================================
  1-BOSQICH — AUTH (KIRISH / CHIQISH)
  Base: /api/v1/auth/
============================================================

--- Ro'yxatdan o'tish ---
POST /api/v1/auth/register/
Body (JSON):
  username    [str]  MAJBURIY
  password    [str]  MAJBURIY
  first_name  [str]  ixtiyoriy
  last_name   [str]  ixtiyoriy
  email       [str]  ixtiyoriy

Misol:
{
    "username": "ulugbek",
    "password": "Secret123!",
    "first_name": "Ulugbek"
}

Javob (201):
{
    "message": "Muvaffaqiyatli ro'yxatdan o'tdingiz.",
    "data": {
        "access": "<token>",
        "refresh": "<token>",
        "user": { ... }
    }
}

-------------------------------------------

--- Login ---
POST /api/v1/auth/login/
Body (JSON):
{
    "username": "ulugbek",
    "password": "Secret123!"
}

Javob (200):
{
    "access": "<access_token>",   ← shu tokenni keyingi barcha so'rovlarda ishlating
    "refresh": "<refresh_token>"
}

  * Bundan keyin BARCHA so'rovlarga:
    Header → Authorization: Bearer <access_token>

-------------------------------------------

--- Logout ---
POST /api/v1/auth/logout/
Body (JSON):
{
    "refresh": "<refresh_token>"
}

-------------------------------------------

--- Profilni ko'rish ---
GET /api/v1/auth/profil/

-------------------------------------------

--- Profilni yangilash ---
PATCH /api/v1/auth/profil/
Body (JSON) — faqat o'zgartirilgan maydonlar:
{
    "first_name": "Ulugbek",
    "last_name": "Xatamjonov",
    "email": "ulugbek@gmail.com"
}

-------------------------------------------

--- Parolni o'zgartirish ---
POST /api/v1/auth/change-password/
Body (JSON):
{
    "old_password": "Secret123!",
    "new_password": "NewSecret456!"
}

-------------------------------------------

--- Parol reset (email orqali) ---
POST /api/v1/auth/send-reset-email/
Body (JSON):
{
    "email": "ulugbek@gmail.com"
}
  * Email ga reset havolasi yuboriladi

-------------------------------------------

--- Parolni qayta belgilash ---
POST /api/v1/auth/reset-password/{uid}/{token}/
Body (JSON):
{
    "new_password": "NewSecret456!"
}
  * uid va token — emaildagi havoladan olinadi


============================================================
  2-BOSQICH — STORE (DO'KON)
  Ruxsat: owner
  Base URL: /api/v1/stores/
============================================================

--- Do'kon ro'yxati ---
GET /api/v1/stores/

-------------------------------------------

--- Do'kon detail ---
GET /api/v1/stores/{id}/

Javob:
{
    "id": 1,
    "name": "Baraka Do'koni",
    "owner_name": "Ulugbek",
    "status": "active",
    "created_on": "2026-03-01 | 09:00"
}

-------------------------------------------

--- Do'kon yangilash ---
PATCH /api/v1/stores/{id}/
Body (JSON):
{
    "name": "Baraka Do'koni (yangi nom)"
}

-------------------------------------------

--- Do'konni o'chirish ---
DELETE /api/v1/stores/{id}/


============================================================
  3-BOSQICH — BRANCH (FILIALLAR)
  Ruxsat: list/retrieve → seller+ | create/update/delete → manager+
  Base URL: /api/v1/branches/
============================================================

--- Filial yaratish ---
POST /api/v1/branches/
Body (JSON):
  name     [str]  MAJBURIY — unikal (do'kon ichida)
  address  [str]  ixtiyoriy
  phone    [str]  ixtiyoriy

Misol:
{
    "name": "Baraka filial 1",
    "address": "Toshkent, Chilonzor 5",
    "phone": "+998991234567"
}

Javob (201):
{
    "message": "Filial muvaffaqiyatli yaratildi.",
    "data": {
        "id": 1,
        "name": "Baraka filial 1",
        "address": "Toshkent, Chilonzor 5",
        "status": "active",
        "status_display": "Faol"
    }
}

-------------------------------------------

--- Filiallar ro'yxati ---
GET /api/v1/branches/
Filter: ?status=active|inactive

-------------------------------------------

--- Filial detail ---
GET /api/v1/branches/{id}/

-------------------------------------------

--- Filial yangilash ---
PATCH /api/v1/branches/{id}/
{
    "name": "Baraka filial 1 (yangi)",
    "status": "inactive"
}

-------------------------------------------

--- Filial o'chirish ---
DELETE /api/v1/branches/{id}/
  * Soft delete — status=inactive


============================================================
  4-BOSQICH — STORESETTINGS (DO'KON SOZLAMALARI)
  Ruxsat: GET → CanAccess('sozlamalar') | PATCH → owner
  Base URL: /api/v1/settings/
  Eslatma: Do'kon yaratilganda avtomatik yaratiladi
============================================================

--- Sozlamalarni ko'rish ---
GET /api/v1/settings/

Javob (asosiy maydonlar):
{
    "id": 1,
    "store_name": "Baraka Do'koni",
    "default_currency": "UZS",
    "shift_enabled": false,
    "subcategory_enabled": true,
    "allow_cash": true,
    "allow_card": true,
    "allow_debt": true,
    "allow_discount": true,
    "require_cash_count": false,
    "low_stock_threshold": 10,
    "auto_pdf": false,
    "show_eur_price": false,
    "show_cny_price": false
}

-------------------------------------------

--- Sozlamalarni yangilash ---
PATCH /api/v1/settings/{id}/
Body (JSON) — faqat o'zgartirilgan maydonlar:
{
    "shift_enabled": true,
    "allow_discount": false,
    "low_stock_threshold": 5,
    "default_currency": "USD"
}

Mavjud default_currency qiymatlari: UZS | USD | EUR | RUB | CNY


============================================================
  5-BOSQICH — WORKER (XODIMLAR)
  Base URL: /api/v1/workers/
============================================================

--- O'z profilini ko'rish ---
GET /api/v1/workers/me/

Javob:
{
    "id": 1,
    "role": "owner",
    "role_display": "Ega",
    "first_name": "Ulugbek",
    "last_name": "Xatamjonov",
    "username": "ulugbek",
    "email": "ulugbek@gmail.com",
    "phone1": "+998991234567",
    "salary": "0.00",
    "status": "active",
    "permissions": ["boshqaruv", "sotuv", "ombor", ...]
}

-------------------------------------------

--- O'z profilini yangilash ---
PATCH /api/v1/workers/me/
Body (JSON) — faqat o'zgartirilgan maydonlar:
{
    "phone1": "+998997654321",
    "email": "new@gmail.com"
}

-------------------------------------------

--- Xodimlar ro'yxati ---
GET /api/v1/workers/
  * Ruxsat: manager+

-------------------------------------------

--- Xodim detail ---
GET /api/v1/workers/{id}/
  * Ruxsat: manager+

-------------------------------------------

--- Yangi xodim qo'shish ---
POST /api/v1/workers/
Body (JSON):
  username    [str]  MAJBURIY
  password    [str]  MAJBURIY
  first_name  [str]  ixtiyoriy
  last_name   [str]  ixtiyoriy
  role        [str]  ixtiyoriy — manager | seller (default: seller)
  branch      [int]  ixtiyoriy — Filial ID
  salary      [num]  ixtiyoriy
  permissions [arr]  ixtiyoriy — rol asosida avtomatik to'ldiriladi

Misol:
{
    "username": "seller1",
    "password": "Seller123!",
    "first_name": "Jasur",
    "role": "seller",
    "branch": 1
}

-------------------------------------------

--- Xodim yangilash ---
PATCH /api/v1/workers/{id}/
{
    "salary": "3000000.00",
    "status": "tatil",
    "permissions": ["sotuv", "savdolar", "mijozlar"]
}

WorkerStatus qiymatlari: active | tatil | ishdan_ketgan

-------------------------------------------

--- Xodim KPI tarixi ---
GET /api/v1/workers/{id}/kpi/
Filter: ?month=3  ?year=2026


============================================================
  6-BOSQICH — CURRENCY (VALYUTA) VA EXCHANGE RATE (KURS)
  Base URL: /api/v1/warehouse/currencies/
            /api/v1/warehouse/exchange-rates/
============================================================

--- Valyutalar ro'yxati ---
GET /api/v1/warehouse/currencies/

Javob:
[
    {"id": 1, "code": "UZS", "name": "O'zbek so'mi", "symbol": "so'm", "is_base": true},
    {"id": 2, "code": "USD", "name": "Amerika dollari", "symbol": "$", "is_base": false}
]

-------------------------------------------

--- Valyuta yaratish ---
POST /api/v1/warehouse/currencies/
Body (JSON):
  code     [str]   MAJBURIY — masalan: "EUR"
  name     [str]   MAJBURIY
  symbol   [str]   MAJBURIY
  is_base  [bool]  ixtiyoriy (faqat bitta base bo'lishi mumkin)

Misol:
{
    "code": "USD",
    "name": "Amerika dollari",
    "symbol": "$"
}

-------------------------------------------

--- Valyuta detail ---
GET /api/v1/warehouse/currencies/{id}/
  * latest_rate maydoni ham keladi

-------------------------------------------

--- Valyuta kursi qo'shish ---
POST /api/v1/warehouse/exchange-rates/
Body (JSON):
  currency  [int]  MAJBURIY — Currency ID
  rate      [num]  MAJBURIY — 1 xorijiy = ? UZS

Misol (1 USD = 12700 UZS):
{
    "currency": 2,
    "rate": "12700.00"
}

-------------------------------------------

--- Kurslar ro'yxati ---
GET /api/v1/warehouse/exchange-rates/
Filter: ?currency=2  ?date=2026-03-19

-------------------------------------------

--- Kurs detail ---
GET /api/v1/warehouse/exchange-rates/{id}/


============================================================
  7-BOSQICH — CATEGORY (KATEGORIYALAR)
  Ruxsat: list/retrieve → seller+ | create/update/delete → manager+
  Base URL: /api/v1/warehouse/categories/
============================================================

--- Kategoriya yaratish ---
POST /api/v1/warehouse/categories/
Body (JSON):
  name         [str]  MAJBURIY — max 200 belgi, do'kon ichida unikal
  description  [str]  ixtiyoriy

Misol:
{
    "name": "Ichimliklar",
    "description": "Sovuq va issiq ichimliklar"
}

Javob (201):
{
    "message": "Kategoriya muvaffaqiyatli yaratildi.",
    "data": {
        "id": 1,
        "name": "Ichimliklar",
        "description": "Sovuq va issiq ichimliklar",
        "store_name": "Baraka Do'koni",
        "status": "active",
        "status_display": "Faol",
        "product_count": 0,
        "subcategory_count": 0,
        "created_on": "2026-03-19 | 09:00"
    }
}

Xato hollari:
  400 — "Kategoriya nomi kiritilishi shart."
  400 — "Bunday nomli Kategoriya mavjud. Iltimos boshqa nom tanlang !"

-------------------------------------------

--- Kategoriyalar ro'yxati ---
GET /api/v1/warehouse/categories/
  * Tartib: active birinchi, keyin inactive

-------------------------------------------

--- Kategoriya detail ---
GET /api/v1/warehouse/categories/{id}/

-------------------------------------------

--- Kategoriya yangilash ---
PATCH /api/v1/warehouse/categories/{id}/
{
    "name": "Ichimliklar (yangilangan)",
    "status": "inactive"
}

  ⚠️ Kategoriya inactive bo'lsa — barcha subkategoriyalari
     ro'yhatda ko'rinmay qoladi (DB da o'zgarmaydi)!

-------------------------------------------

--- Kategoriya o'chirish ---
DELETE /api/v1/warehouse/categories/{id}/
  * Hard delete

Javob (200): {"message": "Kategoriya muvaffaqiyatli o'chirildi."}


============================================================
  8-BOSQICH — SUBCATEGORY (SUBKATEGORIYALAR)
  Base URL: /api/v1/warehouse/subcategories/
  ⚠️ Kategoriya inactive bo'lsa uning subcategorylari ko'rinmaydi
============================================================

--- Subkategoriya yaratish ---
POST /api/v1/warehouse/subcategories/
Body (JSON):
  name         [str]  MAJBURIY
  category     [int]  MAJBURIY — active kategoriya ID
  description  [str]  ixtiyoriy

Misol:
{
    "name": "Gazlangan",
    "category": 1
}

Javob (201):
{
    "message": "Subkategoriya muvaffaqiyatli yaratildi.",
    "data": {
        "id": 1,
        "name": "Gazlangan",
        "category_id": 1,
        "category_name": "Ichimliklar",
        "status": "active",
        "product_count": 0
    }
}

-------------------------------------------

--- Subkategoriyalar ro'yxati ---
GET /api/v1/warehouse/subcategories/
Filter: ?category=1

-------------------------------------------

--- Subkategoriya detail ---
GET /api/v1/warehouse/subcategories/{id}/

-------------------------------------------

--- Subkategoriya yangilash ---
PATCH /api/v1/warehouse/subcategories/{id}/
{
    "name": "Gazlangan (yangi)",
    "status": "inactive"
}

-------------------------------------------

--- Subkategoriya o'chirish ---
DELETE /api/v1/warehouse/subcategories/{id}/


============================================================
  9-BOSQICH — PRODUCTS (MAHSULOTLAR)
  Base URL: /api/v1/warehouse/products/
  Oldin: Category (va ixtiyoriy SubCategory) yaratilgan bo'lsin
============================================================

--- Mahsulot yaratish ---
POST /api/v1/warehouse/products/
Body (form-data — rasm yuklash uchun):
  name            [str]   MAJBURIY — max 300 belgi, unikal
  category        [int]   MAJBURIY — Category ID
  subcategory     [int]   ixtiyoriy
  unit            [str]   MAJBURIY — piece | kg | litre | box | meter
  sale_price      [num]   MAJBURIY — sotish narxi
  purchase_price  [num]   ixtiyoriy (AVCO kirimda avtomatik yangilaydi)
  price_currency  [int]   ixtiyoriy — Currency ID
  currency_code   [str]   ixtiyoriy — "UZS" | "USD" | "EUR" | "RUB" | "CNY"
  barcode         [str]   ixtiyoriy — bo'sh qolsa avtomatik EAN-13
  image           [file]  ixtiyoriy — mahsulot rasmi (Cloudinary ga yuklaydi)

  ⚠️ price_currency (ID) YOKI currency_code (matn) — bittasini yuboring.
     Ikkalasi yuborilsa price_currency ustunlik qiladi.

Misol (JSON):
{
    "name": "Coca-Cola 0.5L",
    "category": 1,
    "subcategory": 1,
    "unit": "piece",
    "sale_price": "5000.00",
    "currency_code": "UZS"
}

Javob (201):
{
    "message": "Mahsulot muvaffaqiyatli yaratildi.",
    "data": {
        "id": 5,
        "name": "Coca-Cola 0.5L",
        "category_id": 1,
        "category_name": "Ichimliklar",
        "subcategory_id": 1,
        "subcategory_name": "Gazlangan",
        "unit": "piece",
        "unit_display": "Dona",
        "purchase_price": "0.00",
        "sale_price": "5000.00",
        "currency_id": 1,
        "currency_code": "UZS",
        "currency_symbol": "so'm",
        "barcode": "2000016000005",
        "barcode_image_url": "https://.../warehouse/products/5/barcode/",
        "image": null,
        "status": "active",
        "status_display": "Faol",
        "stock_total": 0,
        "created_on": "2026-03-19 | 10:00"
    }
}

Xato hollari:
  400 — "Mahsulot nomi kiritilishi shart."
  400 — "Bunday nomli Mahsulot mavjud. Iltimos boshqa nom tanlang !"
  400 — "'YEUR' valyuta kodi topilmadi."

-------------------------------------------

--- Mahsulotlar ro'yxati ---
GET /api/v1/warehouse/products/
Filter: ?category=1  ?status=active|inactive

Javob maydoni:
  id, name, category_name, subcategory_name, unit, unit_display
  sale_price, currency_code  (null bo'lsa null qaytaradi, yo'qolmaydi)
  barcode, barcode_image_url, image, status, status_display

-------------------------------------------

--- Mahsulot detail ---
GET /api/v1/warehouse/products/{id}/

-------------------------------------------

--- Barcode rasmi (PNG) ---
GET /api/v1/warehouse/products/{id}/barcode/
  * Javob: PNG rasm (binary)
  * ?format=svg  → SVG formatda

-------------------------------------------

--- QR-kod rasmi ---
GET /api/v1/warehouse/products/{id}/qr/
  * Javob: PNG rasm

-------------------------------------------

--- Barcode/QR orqali mahsulot qidirish ---
GET /api/v1/warehouse/products/scan/?code=2000016000005
  * Skanerlangan barcode yoki QR matnini ?code= ga bering
  * Javob: ProductDetail (bitta mahsulot)

Xato hollari:
  400 — "code parametri kiritilishi shart."
  404 — "Bu barcode/QR kod bo'yicha mahsulot topilmadi."

-------------------------------------------

--- Bulk QR-kodlar (ZIP) ---
POST /api/v1/warehouse/products/bulk-qr/
Body (JSON):
{
    "product_ids": [5, 8, 11],
    "copies": 2
}
  * Javob: ZIP fayl (har mahsulot × copies dona QR PNG)
  * Maksimum: 500 ta QR

-------------------------------------------

--- Mahsulot yangilash ---
PATCH /api/v1/warehouse/products/{id}/
Body (JSON) — faqat o'zgartirilgan maydonlar:
{
    "sale_price": "5500.00",
    "currency_code": "USD",
    "status": "inactive"
}

-------------------------------------------

--- Mahsulot o'chirish ---
DELETE /api/v1/warehouse/products/{id}/
  * Soft delete → status=inactive


============================================================
  10-BOSQICH — SUPPLIER (YETKAZIB BERUVCHI)
  Base URL: /api/v1/warehouse/suppliers/
============================================================

--- Supplier yaratish ---
POST /api/v1/warehouse/suppliers/
Body (JSON):
  name     [str]  MAJBURIY — unikal (do'kon ichida)
  phone    [str]  ixtiyoriy
  address  [str]  ixtiyoriy
  note     [str]  ixtiyoriy

Misol:
{
    "name": "Maysara LLC",
    "phone": "+998991234567",
    "address": "Toshkent, Chilonzor"
}

Javob (201):
{
    "message": "Yetkazib beruvchi muvaffaqiyatli qo'shildi.",
    "data": {
        "id": 1,
        "name": "Maysara LLC",
        "phone": "+998991234567",
        "debt_balance": "0.00",
        "status": "active"
    }
}

-------------------------------------------

--- Supplierlar ro'yxati ---
GET /api/v1/warehouse/suppliers/
Filter: ?status=active|inactive

-------------------------------------------

--- Supplier detail ---
GET /api/v1/warehouse/suppliers/{id}/

-------------------------------------------

--- Supplier yangilash ---
PATCH /api/v1/warehouse/suppliers/{id}/
{
    "phone": "+998990000000",
    "status": "inactive"
}

-------------------------------------------

--- Supplier o'chirish ---
DELETE /api/v1/warehouse/suppliers/{id}/
  * Soft delete

-------------------------------------------

--- Supplier to'lov (qarzni kamaytirish) ---
POST /api/v1/warehouse/supplier-payments/
Body (JSON):
  supplier      [int]  MAJBURIY — Supplier ID
  amount        [num]  MAJBURIY — musbat son
  payment_type  [str]  MAJBURIY — cash | card | transfer
  note          [str]  ixtiyoriy

Misol:
{
    "supplier": 1,
    "amount": "500000.00",
    "payment_type": "cash",
    "note": "Oylik to'lov"
}

  * Saqlanganida: supplier.debt_balance -= amount

-------------------------------------------

--- To'lovlar ro'yxati ---
GET /api/v1/warehouse/supplier-payments/
Filter: ?supplier=1  ?smena=1

  ⚠️ Kirim (IN) yaratishda supplier ko'rsatilsa:
     debt_balance += quantity * unit_cost avtomatik oshadi


============================================================
  11-BOSQICH — WAREHOUSE (OMBORLAR)
  Base URL: /api/v1/warehouse/warehouses/
============================================================

--- Ombor yaratish ---
POST /api/v1/warehouse/warehouses/
Body (JSON):
  name     [str]  MAJBURIY — unikal (do'kon ichida)
  address  [str]  ixtiyoriy

Misol:
{
    "name": "Asosiy ombor",
    "address": "Toshkent, Yakkasaroy"
}

-------------------------------------------

--- Omborlar ro'yxati ---
GET /api/v1/warehouse/warehouses/
Filter: ?status=active|inactive

-------------------------------------------

--- Ombor detail (ichidagi mahsulotlar bilan) ---
GET /api/v1/warehouse/warehouses/{id}/

Javob:
{
    "id": 1,
    "name": "Asosiy ombor",
    "status": "active",
    "products": [
        {
            "product_id": 5,
            "product_name": "Coca-Cola 0.5L",
            "quantity": "120.000",
            "purchase_price": "3500.00",
            "sale_price": "5000.00",
            "barcode": "2000016000005",
            "barcode_image_url": "https://.../products/5/barcode/",
            "added_on": "2026-03-19 | 10:43"
        }
    ]
}

-------------------------------------------

--- Ombor yangilash ---
PATCH /api/v1/warehouse/warehouses/{id}/
{
    "name": "Asosiy ombor (yangi)",
    "status": "inactive"
}

-------------------------------------------

--- Ombor o'chirish ---
DELETE /api/v1/warehouse/warehouses/{id}/
  * Soft delete


============================================================
  12-BOSQICH — SMENA (SHIFT)
  shift_enabled=True bo'lsa sotuvdan OLDIN smena ochish SHART
  Base URL: /api/v1/shifts/
============================================================

--- Smena ochish ---
POST /api/v1/shifts/
Body (JSON):
  branch      [int]  MAJBURIY — Filial ID
  cash_start  [num]  ixtiyoriy — Boshlang'ich naqd pul (default: 0)
  note        [str]  ixtiyoriy

Misol:
{
    "branch": 1,
    "cash_start": 500000,
    "note": "Ertalabki smena"
}

Javob (201):
{
    "message": "Smena muvaffaqiyatli ochildi.",
    "data": {
        "id": 1,
        "branch_name": "Baraka filial 1",
        "status": "open",
        "cash_start": "500000.00",
        "opened_at": "2026-03-19 | 09:00"
    }
}

-------------------------------------------

--- Smenalar ro'yxati ---
GET /api/v1/shifts/
Filter: ?branch=1  ?status=open|closed

-------------------------------------------

--- Smena detail ---
GET /api/v1/shifts/{id}/

-------------------------------------------

--- X-Report (smena davomidagi hisobot) ---
GET /api/v1/shifts/{id}/x-report/
  * Smena ochiq bo'lsa ham olib bo'ladi
  * Sotuv soni, tushum, xarajatlar

-------------------------------------------

--- Smena yopish ---
PATCH /api/v1/shifts/{id}/close/
Body (JSON):
{
    "cash_end": 750000,
    "note": "Kun oxiri"
}
  * require_cash_count=True bo'lsa cash_end MAJBURIY

-------------------------------------------

--- Z-Report (yopilgan smena yakuniy hisoboti) ---
GET /api/v1/shifts/{id}/z-report/
  * Faqat yopilgan smena uchun ishlaydi


============================================================
  13-BOSQICH — STOCKMOVEMENT (KIRIM / CHIQIM)
  DIQQAT: branch YOKI warehouse — faqat BITTASINI yuboring!
  Base URL: /api/v1/warehouse/movements/
============================================================

--- KIRIM (IN) — bitta mahsulot ---
POST /api/v1/warehouse/movements/
Body (JSON):
  product        [int]  MAJBURIY — Product ID
  branch         [int]  shart*   — Filial ID
  warehouse      [int]  shart*   — Ombor ID   (* bittasi bo'lishi shart)
  movement_type  [str]  MAJBURIY — "in"
  quantity       [num]  MAJBURIY — musbat son
  unit_cost      [num]  ixtiyoriy — xarid narxi (FIFO batch va AVCO yangilaydi)
  supplier       [int]  ixtiyoriy — Supplier ID (debt_balance oshadi)
  note           [str]  ixtiyoriy

Misol (filiallga):
{
    "product": 5,
    "branch": 1,
    "movement_type": "in",
    "quantity": "100.000",
    "unit_cost": "3500.00",
    "supplier": 1,
    "note": "Yangi tovar keldi"
}

Misol (omborga):
{
    "product": 5,
    "warehouse": 1,
    "movement_type": "in",
    "quantity": "200.000",
    "unit_cost": "3500.00"
}

Javob (201):
{
    "message": "Harakat muvaffaqiyatli qayd etildi.",
    "data": { ...MovementDetail... }
}

-------------------------------------------

--- CHIQIM (OUT) ---
POST /api/v1/warehouse/movements/
{
    "product": 5,
    "branch": 1,
    "movement_type": "out",
    "quantity": "5.000"
}

  * unit_cost OUT da e'tiborsiz — FIFO dan avtomatik hisoblanadi
  * Qoldiq yetmasa → 400 xato

Xato holati:
  400 — "Qoldiq yetarli emas. 'Filial1' da 'Coca-Cola' qoldig'i: 10, so'ralgan: 50."

-------------------------------------------

--- GURUHLI KIRIM/CHIQIM (BULK — atomic) ---
POST /api/v1/warehouse/movements/bulk/

  * Bir so'rovda N ta mahsulot
  * Bitta xato → barchasi rollback (hech narsa saqlanmaydi)

Body (JSON):
  movement_type  [str]  MAJBURIY — "in" | "out"
  branch         [int]  shart*   — Filial ID
  warehouse      [int]  shart*   — Ombor ID
  note           [str]  ixtiyoriy
  items          [arr]  MAJBURIY — kamida 1 ta
    items[].product   [int]  MAJBURIY
    items[].quantity  [num]  MAJBURIY — musbat son
    items[].unit_cost [num]  ixtiyoriy (IN uchun)
    items[].supplier  [int]  ixtiyoriy (IN uchun)

Misol (3 mahsulot kirim):
{
    "movement_type": "in",
    "branch": 1,
    "note": "Maysaradan kirim",
    "items": [
        {"product": 5, "quantity": 100, "unit_cost": 3500, "supplier": 1},
        {"product": 8, "quantity": 50,  "unit_cost": 8000},
        {"product": 11,"quantity": 200, "unit_cost": 5000}
    ]
}

Javob (201):
{
    "message": "3 ta harakat muvaffaqiyatli qayd etildi.",
    "data": [ ...MovementDetail x3... ]
}

Xato (hech narsa saqlanmaydi):
{
    "items[3]": "Coca-Cola qoldig'i yetarli emas (1-filial): mavjud 30, so'ralgan 200."
}

-------------------------------------------

--- Harakatlar ro'yxati ---
GET /api/v1/warehouse/movements/
Filter: ?product=1  ?branch=1  ?warehouse=1  ?movement_type=in|out

-------------------------------------------

--- Harakat detail ---
GET /api/v1/warehouse/movements/{id}/


============================================================
  14-BOSQICH — STOCK (QOLDIQLAR)
  Base URL: /api/v1/warehouse/stocks/
============================================================

--- Barcha qoldiqlar ---
GET /api/v1/warehouse/stocks/
Filter: ?branch=1  ?warehouse=1  ?product=1

-------------------------------------------

--- Mahsulot bo'yicha guruhlangan qoldiqlar ---
GET /api/v1/warehouse/stocks/by-product/

Javob:
[
    {
        "product_id": 5,
        "product_name": "Coca-Cola 0.5L",
        "product_unit": "Dona",
        "total_quantity": "190.000",
        "locations": [
            {
                "stock_id": 6,
                "location_type": "branch",
                "location_id": 1,
                "location_name": "Baraka filial 1",
                "quantity": "70.000",
                "updated_on": "2026-03-19 | 10:43"
            },
            {
                "stock_id": 5,
                "location_type": "warehouse",
                "location_id": 1,
                "location_name": "Asosiy ombor",
                "quantity": "120.000",
                "updated_on": "2026-03-19 | 10:43"
            }
        ]
    }
]

-------------------------------------------

--- Kam qoldiqli mahsulotlar ---
GET /api/v1/warehouse/stocks/low-stock/
  * StoreSettings.low_stock_threshold dan kam bo'lganlar

-------------------------------------------

--- Qoldiq detail ---
GET /api/v1/warehouse/stocks/{id}/

-------------------------------------------

--- Qo'lda qoldiq yaratish (boshlang'ich inventarizatsiya) ---
POST /api/v1/warehouse/stocks/
Body (JSON):
{
    "product": 5,
    "branch": 1,
    "quantity": "50.000"
}

-------------------------------------------

--- Qoldiq yangilash ---
PATCH /api/v1/warehouse/stocks/{id}/
{"quantity": "75.000"}

-------------------------------------------

--- Qoldiq o'chirish ---
DELETE /api/v1/warehouse/stocks/{id}/
  * Hard delete


============================================================
  15-BOSQICH — STOCKBATCH (FIFO PARTIYALAR)
  Avtomatik yaratiladi (movement IN + unit_cost da)
  Faqat o'qish mumkin
  Base URL: /api/v1/warehouse/batches/
============================================================

--- Partiyalar ro'yxati ---
GET /api/v1/warehouse/batches/
Filter: ?product=1  ?branch=1  ?warehouse=1

Javob maydoni:
  batch_code   — partiya kodi (STORE-YY-MM-DD-XXXX)
  unit_cost    — bu partiyaning xarid narxi
  qty_received — dastlabki kirim miqdori
  qty_left     — hozirgi qolgan miqdor (0 = partiya tugagan)

-------------------------------------------

--- Partiya detail ---
GET /api/v1/warehouse/batches/{id}/


============================================================
  16-BOSQICH — TRANSFER (JOYLAR ORASIDA O'TKAZISH)
  Base URL: /api/v1/warehouse/transfers/
============================================================

--- Transfer yaratish ---
POST /api/v1/warehouse/transfers/
Body (JSON):
  from_branch     [int]  shart* — Qayerdan (filial)
  from_warehouse  [int]  shart* — Qayerdan (ombor)  (* bittasi)
  to_branch       [int]  shart* — Qayerga (filial)
  to_warehouse    [int]  shart* — Qayerga (ombor)   (* bittasi)
  items           [arr]  MAJBURIY — kamida 1 ta
    items[].product   [int]  MAJBURIY
    items[].quantity  [num]  MAJBURIY
  note            [str]  ixtiyoriy

Misol (filialdan → omborga):
{
    "from_branch": 1,
    "to_warehouse": 1,
    "items": [
        {"product": 5, "quantity": "10.000"},
        {"product": 8, "quantity": "5.000"}
    ],
    "note": "Omborga qaytarish"
}

  ⚠️ status=pending — stock HALI o'zgarmaydi!

-------------------------------------------

--- Transferlar ro'yxati ---
GET /api/v1/warehouse/transfers/
Filter: ?status=pending|confirmed|cancelled

-------------------------------------------

--- Transfer detail ---
GET /api/v1/warehouse/transfers/{id}/

-------------------------------------------

--- Transfer tasdiqlash ---
POST /api/v1/warehouse/transfers/{id}/confirm/
Body: {} (bo'sh)
  * Stock "from" dan ayiriladi, "to" ga qo'shiladi (FIFO)

-------------------------------------------

--- Transfer bekor qilish ---
POST /api/v1/warehouse/transfers/{id}/cancel/
Body: {} (bo'sh)
  * Faqat pending holat bekor qilinadi


============================================================
  17-BOSQICH — WASTAGE (ISROF)
  Yaratilganda StockMovement(OUT) avtomatik yaratiladi
  Base URL: /api/v1/warehouse/wastages/
============================================================

--- Isrof yaratish ---
POST /api/v1/warehouse/wastages/
Body (JSON):
  product    [int]  MAJBURIY
  branch     [int]  shart*   — Filial ID
  warehouse  [int]  shart*   — Ombor ID  (* bittasi)
  quantity   [num]  MAJBURIY — mavjud qoldiqdan oshmaydi
  reason     [str]  ixtiyoriy — sabab

Misol:
{
    "product": 5,
    "branch": 1,
    "quantity": "3.000",
    "reason": "Muddati o'tdi"
}

Xato holati:
  400 — "Qoldiq yetarli emas."

-------------------------------------------

--- Isroflar ro'yxati ---
GET /api/v1/warehouse/wastages/
Filter: ?product=1  ?branch=1  ?warehouse=1

-------------------------------------------

--- Isrof detail ---
GET /api/v1/warehouse/wastages/{id}/


============================================================
  18-BOSQICH — STOCK AUDIT (INVENTARIZATSIYA)
  Base URL: /api/v1/warehouse/audits/
============================================================

--- Inventarizatsiya yaratish ---
POST /api/v1/warehouse/audits/
Body (JSON):
  branch     [int]  shart* — Filial ID
  warehouse  [int]  shart* — Ombor ID  (* bittasi)
  note       [str]  ixtiyoriy

Misol:
{
    "branch": 1,
    "note": "Oylik inventarizatsiya"
}

  * Yaratilganda: mavjud barcha Stock → audit items ga ko'chiriladi
  * status=draft

-------------------------------------------

--- Inventarizatsiyalar ro'yxati ---
GET /api/v1/warehouse/audits/
Filter: ?status=draft|confirmed  ?branch=1  ?warehouse=1

-------------------------------------------

--- Audit detail (items bilan) ---
GET /api/v1/warehouse/audits/{id}/

Javob:
{
    "id": 1,
    "branch_name": "Baraka filial 1",
    "status": "draft",
    "items": [
        {
            "id": 10,
            "product_name": "Coca-Cola 0.5L",
            "system_quantity": "70.000",   ← tizimda bor miqdor
            "actual_quantity": null,       ← hisoblangan miqdor (siz kiritasiz)
            "difference": null
        }
    ]
}

-------------------------------------------

--- Audit item yangilash (haqiqiy miqdorni kiritish) ---
PATCH /api/v1/warehouse/audits/{id}/items/{item_id}/
Body (JSON):
{
    "actual_quantity": "65.000"
}

-------------------------------------------

--- Inventarizatsiyani tasdiqlash ---
POST /api/v1/warehouse/audits/{id}/confirm/
Body: {} (bo'sh)
  * actual < system → OUT StockMovement yaratiladi
  * actual > system → IN StockMovement yaratiladi
  * status=confirmed

-------------------------------------------

--- Inventarizatsiyani bekor qilish ---
POST /api/v1/warehouse/audits/{id}/cancel/
Body: {} (bo'sh)
  * Faqat draft holat bekor qilinadi


============================================================
  19-BOSQICH — SALE (SOTUV)
  Oldin: Stock da mahsulot bo'lsin
  shift_enabled=True bo'lsa smena ochiq bo'lsin
  Base URL: /api/v1/sales/
============================================================

--- Sotuv yaratish — NAQD ---
POST /api/v1/sales/
Body (JSON):
  branch          [int]  MAJBURIY
  payment_type    [str]  MAJBURIY — cash | card | debt
  paid_amount     [num]  MAJBURIY
  items           [arr]  MAJBURIY — kamida 1 ta
    items[].product    [int]  MAJBURIY
    items[].quantity   [num]  MAJBURIY — min: 0.001
    items[].unit_price [num]  ixtiyoriy — berilmasa product.sale_price
  customer        [int]  ixtiyoriy
  discount_amount [num]  ixtiyoriy (default: 0)
  note            [str]  ixtiyoriy

Misol (naqd):
{
    "branch": 1,
    "payment_type": "cash",
    "paid_amount": "10000.00",
    "items": [
        {"product": 5, "quantity": "2.000"},
        {"product": 8, "quantity": "1.000", "unit_price": "4500.00"}
    ]
}

-------------------------------------------

--- Sotuv yaratish — NASIYA ---
{
    "branch": 1,
    "customer": 3,
    "payment_type": "debt",
    "paid_amount": "0.00",
    "items": [
        {"product": 5, "quantity": "1.000"}
    ]
}
  * paid_amount < total → qolgan qism customer.debt_balance ga qo'shiladi

-------------------------------------------

--- Sotuv yaratish — KARTA ---
{
    "branch": 1,
    "payment_type": "card",
    "paid_amount": "25000.00",
    "items": [
        {"product": 5, "quantity": "5.000"}
    ]
}

Xato hollari:
  400 — "Qoldiq yetarli emas. 'Mahsulot1' uchun qoldiq: 3, so'ralgan: 5."
  400 — "Naqd to'lov taqiqlangan (allow_cash=False)."
  400 — "Chegirma ruxsat etilmagan (allow_discount=False)."
  400 — "Ochiq smena topilmadi. Avval smenani oching."

-------------------------------------------

--- Sotuvlar ro'yxati ---
GET /api/v1/sales/
Filter: ?branch=1  ?status=completed|cancelled
        ?payment_type=cash|card|debt  ?smena=1

-------------------------------------------

--- Sotuv detail ---
GET /api/v1/sales/{id}/

Javob asosiy maydonlari:
  total_price, discount_amount, paid_amount, debt_amount, items[]

-------------------------------------------

--- Sotuv bekor qilish ---
PATCH /api/v1/sales/{id}/cancel/
Body: {} (bo'sh)
  * Stock qaytariladi (StockMovement IN avtomatik)
  * Mijoz qarzi kamayadi (agar debt bo'lsa)


============================================================
  20-BOSQICH — CUSTOMER GROUP + CUSTOMER (MIJOZLAR)
  Base URL: /api/v1/customer-groups/  va  /api/v1/customers/
============================================================

--- Mijoz guruhi yaratish ---
POST /api/v1/customer-groups/
Body (JSON):
{
    "name": "VIP mijozlar",
    "discount_percent": "10.00"
}

-------------------------------------------

--- Mijoz guruhlari ro'yxati ---
GET /api/v1/customer-groups/

-------------------------------------------

--- Mijoz guruhi yangilash ---
PATCH /api/v1/customer-groups/{id}/
{"name": "Premium"}

-------------------------------------------

--- Mijoz guruhi o'chirish ---
DELETE /api/v1/customer-groups/{id}/

-------------------------------------------

--- Mijoz yaratish ---
POST /api/v1/customers/
Body (JSON):
  name    [str]  MAJBURIY
  phone   [str]  ixtiyoriy
  group   [int]  ixtiyoriy — CustomerGroup ID
  address [str]  ixtiyoriy

Misol:
{
    "name": "Bobur Karimov",
    "phone": "+998901234567",
    "group": 1
}

-------------------------------------------

--- Mijozlar ro'yxati ---
GET /api/v1/customers/
Filter: ?status=active|inactive  ?group=1

-------------------------------------------

--- Mijoz detail ---
GET /api/v1/customers/{id}/

-------------------------------------------

--- Mijoz yangilash ---
PATCH /api/v1/customers/{id}/
{
    "name": "Bobur Karimov (yangi)",
    "status": "inactive"
}

-------------------------------------------

--- Mijoz o'chirish ---
DELETE /api/v1/customers/{id}/
  * Soft delete


============================================================
  21-BOSQICH — SALE RETURN (QAYTARISH)
  Base URL: /api/v1/sale-returns/
============================================================

--- Qaytarish yaratish ---
POST /api/v1/sale-returns/
Body (JSON):
  sale    [int]  MAJBURIY — asl Sale ID
  items   [arr]  MAJBURIY
    items[].sale_item  [int]  MAJBURIY — SaleItem ID
    items[].quantity   [num]  MAJBURIY — qaytariladigan miqdor
  note    [str]  ixtiyoriy

Misol:
{
    "sale": 7,
    "items": [
        {"sale_item": 12, "quantity": "1.000"}
    ],
    "note": "Muddati o'tgan"
}

  * status=pending — stock HALI qaytmaydi!

-------------------------------------------

--- Qaytarishlar ro'yxati ---
GET /api/v1/sale-returns/
Filter: ?status=pending|confirmed|cancelled  ?branch=1  ?smena=1

-------------------------------------------

--- Qaytarish detail ---
GET /api/v1/sale-returns/{id}/

-------------------------------------------

--- Qaytarishni tasdiqlash ---
PATCH /api/v1/sale-returns/{id}/confirm/
Body: {} (bo'sh)
  * StockMovement(IN) avtomatik yaratiladi
  * Mijoz qarzi kamayadi (agar debt sotuv bo'lsa)
  * Ruxsat: manager+

-------------------------------------------

--- Qaytarishni bekor qilish ---
PATCH /api/v1/sale-returns/{id}/cancel/
Body: {} (bo'sh)
  * Ruxsat: manager+


============================================================
  22-BOSQICH — EXPENSE (XARAJATLAR)
  Base URL: /api/v1/expense-categories/  va  /api/v1/expenses/
============================================================

--- Xarajat kategoriyasi yaratish ---
POST /api/v1/expense-categories/
Body (JSON):
{
    "name": "Kommunal",
    "description": "Elektr, suv, gaz"
}

-------------------------------------------

--- Xarajat kategoriyalari ro'yxati ---
GET /api/v1/expense-categories/
Filter: ?status=active|inactive

-------------------------------------------

--- Xarajat kategoriyasi yangilash ---
PATCH /api/v1/expense-categories/{id}/
{"status": "inactive"}

-------------------------------------------

--- Xarajat kategoriyasi o'chirish ---
DELETE /api/v1/expense-categories/{id}/
  * Soft delete

-------------------------------------------

--- Xarajat yaratish ---
POST /api/v1/expenses/
Body (form-data — chek rasmi yuklash uchun):
  branch         [int]   MAJBURIY
  category       [int]   MAJBURIY — ExpenseCategory ID
  amount         [num]   MAJBURIY — musbat son
  description    [str]   ixtiyoriy
  receipt_image  [file]  ixtiyoriy — chek rasmi
  smena          [int]   ixtiyoriy

Misol (JSON):
{
    "branch": 1,
    "category": 2,
    "amount": "150000.00",
    "description": "Elektr to'lovi"
}

-------------------------------------------

--- Xarajatlar ro'yxati ---
GET /api/v1/expenses/
Filter: ?branch=1  ?category=1  ?smena=1  ?date=2026-03-19

-------------------------------------------

--- Xarajat yangilash ---
PATCH /api/v1/expenses/{id}/
{"amount": "200000.00"}

-------------------------------------------

--- Xarajat o'chirish ---
DELETE /api/v1/expenses/{id}/
  * Hard delete


============================================================
  23-BOSQICH — WORKER KPI
  Base URL: /api/v1/kpi/
============================================================

--- KPI ro'yxati ---
GET /api/v1/kpi/
Filter: ?worker=1  ?month=3  ?year=2026

Javob:
[
    {
        "id": 1,
        "worker_name": "Jasur Sobirov",
        "month": 3,
        "year": 2026,
        "total_sales": 15,
        "total_revenue": "750000.00",
        "average_sale": "50000.00",
        "target": null,
        "bonus": null
    }
]

-------------------------------------------

--- KPI detail ---
GET /api/v1/kpi/{id}/

-------------------------------------------

--- KPI maqsad va bonus belgilash ---
PATCH /api/v1/kpi/{id}/set-target/
Body (JSON):
{
    "target": "1000000.00",
    "bonus": "200000.00"
}


============================================================
  24-BOSQICH — DASHBOARD
  Ruxsat: IsAuthenticated + SubscriptionRequired('has_dashboard')
  Base URL: /api/v1/dashboard/
============================================================

--- Dashboard statistika ---
GET /api/v1/dashboard/
Filter:
  ?date_from=2026-03-01
  ?date_to=2026-03-19
  ?branch=1
  ?limit=30     ← chart uchun nuqtalar soni (default: 30)

Javob (8 blok):
{
    "sales": {
        "today_revenue": "250000.00",
        "total_revenue": "5000000.00",
        "sale_count": 45,
        "average_check": "111111.00",
        "growth_percent": 12.5
    },
    "products": {
        "total": 50, "active": 48,
        "low_stock": 3, "out_of_stock": 1
    },
    "customers": {
        "total": 120, "new": 5, "returning": 115
    },
    "expenses": {
        "total": "300000.00",
        "by_category": [...]
    },
    "suppliers": {
        "total": 8, "total_debt": "1500000.00"
    },
    "branches": [
        {"branch_id": 1, "branch_name": "Filial 1", "today_revenue": "250000.00"}
    ],
    "current_smena": {
        "id": 3, "sale_count": 10, "revenue": "150000.00"
    },
    "chart_data": [
        {"date": "2026-03-19", "revenue": "250000.00", "count": 10}
    ]
}

  * Redis kesh: 5 daqiqa TTL


============================================================
  25-BOSQICH — EXPORT / IMPORT (Excel va PDF)
  Ruxsat: Export → IsAuthenticated | Import → IsManagerOrAbove
  Throttling: minutiga 5 ta so'rov
  Base URL: /api/v1/export/
============================================================

--- EXPORT (ma'lumotlarni yuklab olish) ---
  ?format=excel  — .xlsx fayl (default)
  ?format=pdf    — .pdf fayl

GET /api/v1/export/sales/
  Filter: ?date_from= ?date_to= ?branch=1 ?smena=1 ?status=completed

GET /api/v1/export/expenses/
  Filter: ?date_from= ?date_to= ?branch=1 ?smena=1 ?category=1

GET /api/v1/export/stocks/
  Filter: ?branch=1  ?warehouse=1

GET /api/v1/export/stock-movements/
  Filter: ?date_from= ?date_to= ?branch=1 ?warehouse=1 ?movement_type=in|out

GET /api/v1/export/suppliers/
  Filter: ?status=active

Misol:
GET /api/v1/export/sales/?format=excel&date_from=2026-03-01&date_to=2026-03-19
  → .xlsx fayl yuklab olinadi

-------------------------------------------

--- IMPORT shablonini olish (GET) ---
GET /api/v1/export/products/template/         → bo'sh products.xlsx
GET /api/v1/export/customers/template/        → bo'sh customers.xlsx
GET /api/v1/export/stock-movements/template/  → bo'sh movements.xlsx
GET /api/v1/export/suppliers/template/        → bo'sh suppliers.xlsx
GET /api/v1/export/subcategories/template/    → bo'sh subcategories.xlsx

-------------------------------------------

--- IMPORT (POST) ---
POST /api/v1/export/products/import/
Body (form-data):
  file  [file]  MAJBURIY — to'ldirilgan .xlsx fayl

Javob (200):
{
    "created": 10,
    "skipped": 2,
    "errors": ["3-qator: mahsulot nomi bo'sh"]
}

POST /api/v1/export/customers/import/
POST /api/v1/export/stock-movements/import/
POST /api/v1/export/suppliers/import/
POST /api/v1/export/subcategories/import/


============================================================
  26-BOSQICH — AUDIT LOG
  Ruxsat: faqat owner
  Base URL: /api/v1/audit-logs/
============================================================

--- Audit log ro'yxati ---
GET /api/v1/audit-logs/
Filter: ?model=Product  ?action=create|update|delete
        ?worker=1  ?date_from=2026-03-01  ?date_to=2026-03-19

Javob:
[
    {
        "id": 1,
        "model": "Product",
        "action": "create",
        "description": "Mahsulot yaratildi: 'Coca-Cola 0.5L'",
        "worker_name": "Jasur Sobirov",
        "created_on": "2026-03-19 | 10:00"
    }
]

-------------------------------------------

--- Audit log detail ---
GET /api/v1/audit-logs/{id}/


============================================================
  27-BOSQICH — SUBSCRIPTION (OBUNA)
  Base URL: /api/v1/subscription/
============================================================

--- Joriy obuna holati ---
GET /api/v1/subscription/

Javob:
{
    "plan_name": "Pro",
    "plan_type": "pro",
    "status": "active",
    "start_date": "2026-02-01",
    "end_date": "2026-05-01",
    "days_left": 42,
    "features": {
        "has_export": true,
        "has_dashboard": true,
        "has_audit_log": true,
        "max_branches": 5,
        "max_warehouses": 3,
        "max_workers": 20,
        "max_products": 0
    }
}

-------------------------------------------

--- Tarif rejalari ---
GET /api/v1/subscription/plans/
  * Javob: [{ plan nomi, narxi, limitlar, featurelar }, ...]

-------------------------------------------

--- To'lov tarixi ---
GET /api/v1/subscription/invoices/

-------------------------------------------

--- SUPERADMIN: Obunarlar ro'yxati ---
GET /api/v1/admin/subscriptions/
Filter: ?status=trial|active|expired|cancelled  ?plan_type=trial|basic|pro|enterprise

-------------------------------------------

--- SUPERADMIN: Obuna detail ---
GET /api/v1/admin/subscriptions/{id}/

-------------------------------------------

--- SUPERADMIN: Obunani o'zgartirish ---
PATCH /api/v1/admin/subscriptions/{id}/
Body (JSON):
{
    "plan": 2,
    "status": "active",
    "end_date": "2026-06-01"
}

-------------------------------------------

--- SUPERADMIN: Muddat uzaytirish ---
POST /api/v1/admin/subscriptions/{id}/extend/
Body (JSON):
{
    "days": 30,
    "note": "Bonus 1 oy"
}

-------------------------------------------

--- SUPERADMIN: To'lov qo'shish ---
POST /api/v1/admin/subscriptions/{id}/add-invoice/
Body (JSON):
{
    "amount": "500000.00",
    "is_yearly": false,
    "note": "Oylik to'lov"
}


============================================================
  QISQACHA ESLATMALAR
============================================================

1. branch YOKI warehouse — harakatlar, stock, transferlarda
   faqat BITTASINI yuborasiz, ikkalasini emas!

2. FIFO tartibi — OUT harakatda eng eski partiya avval chiqariladi.
   unit_cost OUT da e'tiborsiz (avtomatik hisoblanadi).

3. Bulk movement (atomic) — bitta xato bo'lsa barchasi bekor qilinadi.

4. Transfer confirm — faqat shundan keyin stock o'zgaradi.
   Pending holatda hech narsa o'zgarmaydi.

5. StockAudit confirm — actual vs system farqiga qarab
   avtomatik IN yoki OUT movement yaratiladi.

6. Smena — shift_enabled=True bo'lsa sotuv uchun
   ochiq smena bo'lishi shart.

7. Kategoriya inactive → uning subkategoriyalari ro'yhatda
   ko'rinmaydi (DB da o'zgarmaydi).

8. currency_code ("UZS"/"USD"/"EUR") YOKI price_currency (ID) —
   bittasini yuboring. Ikkalasi yuborilsa ID ustunlik qiladi.

9. Supplier + kirim — StockMovement(IN, supplier=X) yaratilsa
   debt_balance oshadi. SupplierPayment yaratilsa kamayadi.

10. Soft delete — Category, SubCategory, Product, Customer,
    Warehouse, Supplier, Branch, ExpenseCategory → status=inactive.
    Hard delete — Stock, Expense → bazadan butunlay o'chadi.

11. purchase_price (AVCO) — kirim(IN) qilinganda avtomatik
    yangilanadi. Qo'lda o'zgartirilmaydi.

12. Subscription (ReadOnlyIfExpired) — obuna tugagan do'kondan
    faqat GET so'rovlari o'tadi. Yozish uchun obunani yangilash kerak.


============================================================
  TAVSIYA ETILGAN TEST TARTIBI — TO'LIQ (46 qadam)
============================================================

  [1]  POST /api/v1/auth/register/                    — Ro'yxatdan o'tish
  [2]  POST /api/v1/auth/login/                        — Login, token olish
  [3]  GET  /api/v1/stores/                            — Do'kon ro'yxati
  [4]  GET  /api/v1/settings/                          — Sozlamalarni ko'rish
  [5]  PATCH /api/v1/settings/{id}/                   — Sozlamalarni yangilash
  [6]  POST /api/v1/branches/                          — Filial yaratish
  [7]  POST /api/v1/workers/                           — Xodim qo'shish
  [8]  GET  /api/v1/workers/me/                        — O'z profili
  [9]  POST /api/v1/warehouse/currencies/              — Valyuta yaratish
  [10] POST /api/v1/warehouse/exchange-rates/          — Kurs kiritish
  [11] POST /api/v1/warehouse/categories/              — Kategoriya yaratish
  [12] POST /api/v1/warehouse/subcategories/           — Subkategoriya yaratish
  [13] POST /api/v1/warehouse/suppliers/               — Supplier yaratish
  [14] POST /api/v1/warehouse/warehouses/              — Ombor yaratish
  [15] POST /api/v1/warehouse/products/                — Mahsulot yaratish
  [16] GET  /api/v1/warehouse/products/{id}/           — Detail (barcode_image_url, image)
  [17] GET  /api/v1/warehouse/products/{id}/barcode/   — Barcode PNG rasmi
  [18] GET  /api/v1/warehouse/products/{id}/qr/        — QR PNG rasmi
  [19] GET  /api/v1/warehouse/products/scan/?code=...  — Barcode qidirish
  [20] POST /api/v1/warehouse/products/bulk-qr/        — Bulk QR ZIP
  [21] POST /api/v1/shifts/                            — Smena ochish
  [22] POST /api/v1/warehouse/movements/               — Bitta kirim (IN)
  [23] POST /api/v1/warehouse/movements/bulk/          — Guruhli kirim (bulk IN)
  [24] GET  /api/v1/warehouse/stocks/                  — Qoldiqlar
  [25] GET  /api/v1/warehouse/stocks/by-product/       — Mahsulot bo'yicha qoldiq
  [26] GET  /api/v1/warehouse/stocks/low-stock/        — Kam qoldiqlilar
  [27] GET  /api/v1/warehouse/batches/                 — FIFO partiyalar
  [28] POST /api/v1/warehouse/movements/ (out)         — Chiqim
  [29] POST /api/v1/warehouse/transfers/               — Transfer yaratish
  [30] POST /api/v1/warehouse/transfers/{id}/confirm/  — Transfer tasdiqlash
  [31] POST /api/v1/warehouse/wastages/                — Isrof
  [32] POST /api/v1/warehouse/audits/                  — Inventarizatsiya yaratish
  [33] PATCH /api/v1/warehouse/audits/{id}/items/{item_id}/ — Haqiqiy miqdor
  [34] POST /api/v1/warehouse/audits/{id}/confirm/     — Inventarizatsiya tasdiqlash
  [35] POST /api/v1/customer-groups/                   — Mijoz guruhi
  [36] POST /api/v1/customers/                         — Mijoz yaratish
  [37] POST /api/v1/sales/ (cash)                      — Naqd sotuv
  [38] POST /api/v1/sales/ (debt)                      — Nasiya sotuv
  [39] GET  /api/v1/sales/{id}/                        — Sotuv detail
  [40] POST /api/v1/sale-returns/                      — Qaytarish yaratish
  [41] PATCH /api/v1/sale-returns/{id}/confirm/        — Qaytarish tasdiqlash
  [42] POST /api/v1/expense-categories/                — Xarajat kategoriyasi
  [43] POST /api/v1/expenses/                          — Xarajat yaratish
  [44] GET  /api/v1/shifts/{id}/x-report/              — X-Report
  [45] PATCH /api/v1/shifts/{id}/close/                — Smena yopish
  [46] GET  /api/v1/shifts/{id}/z-report/              — Z-Report
  [47] GET  /api/v1/dashboard/                         — Dashboard statistika
  [48] GET  /api/v1/export/sales/?format=excel         — Excel eksport
  [49] GET  /api/v1/export/products/template/          — Import shabloni
  [50] POST /api/v1/export/products/import/            — Excel import
  [51] GET  /api/v1/kpi/                               — WorkerKPI
  [52] PATCH /api/v1/kpi/{id}/set-target/              — KPI maqsad belgilash
  [53] GET  /api/v1/audit-logs/                        — Audit log
  [54] GET  /api/v1/subscription/                      — Obuna holati

============================================================
  Sana: 19.03.2026  |  Shop CRM System v1.0  |  54 test qadam
============================================================
