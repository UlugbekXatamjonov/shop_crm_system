"""
============================================================
WAREHOUSE APP — API URL'lari
============================================================
Prefix: /api/v1/warehouse/

Router avtomatik quyidagi URL'larni yaratadi:

  GET    /api/v1/warehouse/categories/           — kategoriyalar ro'yxati
  POST   /api/v1/warehouse/categories/           — kategoriya yaratish
  GET    /api/v1/warehouse/categories/{id}/      — kategoriya tafsilotlari
  PATCH  /api/v1/warehouse/categories/{id}/      — kategoriya yangilash
  DELETE /api/v1/warehouse/categories/{id}/      — kategoriyani nofaol qilish

  GET    /api/v1/warehouse/subcategories/        — subkategoriyalar ro'yxati (?category=<id>)
  POST   /api/v1/warehouse/subcategories/        — subkategoriya yaratish
  GET    /api/v1/warehouse/subcategories/{id}/   — subkategoriya tafsilotlari
  PATCH  /api/v1/warehouse/subcategories/{id}/   — subkategoriya yangilash
  DELETE /api/v1/warehouse/subcategories/{id}/   — subkategoriyani nofaol qilish

  GET    /api/v1/warehouse/currencies/           — valyutalar ro'yxati
  POST   /api/v1/warehouse/currencies/           — valyuta qo'shish (manager+)
  GET    /api/v1/warehouse/currencies/{id}/      — valyuta tafsilotlari (latest_rate bilan)

  GET    /api/v1/warehouse/exchange-rates/       — kurslar ro'yxati (?currency=USD&date=2026-03-03)
  POST   /api/v1/warehouse/exchange-rates/       — kurs qo'lda kiritish (manager+)
  GET    /api/v1/warehouse/exchange-rates/{id}/  — kurs tafsilotlari

  GET    /api/v1/warehouse/products/             — mahsulotlar ro'yxati (?category=&subcategory=&status=)
  POST   /api/v1/warehouse/products/             — mahsulot yaratish (barcode auto-generate)
  GET    /api/v1/warehouse/products/{id}/        — mahsulot tafsilotlari
  PATCH  /api/v1/warehouse/products/{id}/        — mahsulot yangilash
  DELETE /api/v1/warehouse/products/{id}/        — mahsulotni nofaol qilish
  GET    /api/v1/warehouse/products/{id}/barcode/— barcode PNG/SVG rasm (?format=svg)

  GET    /api/v1/warehouse/warehouses/           — omborlar ro'yxati
  POST   /api/v1/warehouse/warehouses/           — yangi ombor qo'shish (manager+)
  GET    /api/v1/warehouse/warehouses/{id}/      — ombor tafsilotlari
  PATCH  /api/v1/warehouse/warehouses/{id}/      — ombor yangilash (manager+)
  DELETE /api/v1/warehouse/warehouses/{id}/      — omborni nofaol qilish (manager+, soft delete)

  GET    /api/v1/warehouse/stocks/               — qoldiqlar ro'yxati (branch|warehouse)
  POST   /api/v1/warehouse/stocks/               — qoldiq qo'shish (branch yoki warehouse)
  GET    /api/v1/warehouse/stocks/{id}/          — qoldiq tafsilotlari
  PATCH  /api/v1/warehouse/stocks/{id}/          — qoldiqni yangilash
  DELETE /api/v1/warehouse/stocks/{id}/          — qoldiqni o'chirish

  GET    /api/v1/warehouse/movements/            — harakatlar ro'yxati (branch|warehouse)
  POST   /api/v1/warehouse/movements/            — harakat yaratish (kirim/chiqim, branch yoki warehouse)
  GET    /api/v1/warehouse/movements/{id}/       — harakat tafsilotlari

  GET    /api/v1/warehouse/transfers/            — transferlar ro'yxati
  POST   /api/v1/warehouse/transfers/            — yangi transfer (pending holat)
  GET    /api/v1/warehouse/transfers/{id}/       — transfer tafsilotlari
  POST   /api/v1/warehouse/transfers/{id}/confirm/ — tasdiqlash (stock yangilanadi, FIFO)
  POST   /api/v1/warehouse/transfers/{id}/cancel/  — bekor qilish (faqat pending)

  GET    /api/v1/warehouse/batches/              — FIFO partiyalar ro'yxati (?product=<id>)
  GET    /api/v1/warehouse/batches/{id}/         — partiya tafsilotlari
"""

from rest_framework.routers import DefaultRouter

from .views import (
    CategoryViewSet,
    CurrencyViewSet,
    ExchangeRateViewSet,
    ProductViewSet,
    StockBatchViewSet,
    StockMovementViewSet,
    StockViewSet,
    SubCategoryViewSet,
    TransferViewSet,
    WarehouseViewSet,
)

router = DefaultRouter()
router.register(r'categories',     CategoryViewSet,      basename='category')
router.register(r'subcategories',  SubCategoryViewSet,   basename='subcategory')
router.register(r'currencies',     CurrencyViewSet,      basename='currency')
router.register(r'exchange-rates', ExchangeRateViewSet,  basename='exchange-rate')
router.register(r'products',       ProductViewSet,       basename='product')
router.register(r'warehouses',     WarehouseViewSet,     basename='warehouse')
router.register(r'stocks',         StockViewSet,         basename='stock')
router.register(r'movements',      StockMovementViewSet, basename='movement')
router.register(r'transfers',      TransferViewSet,      basename='transfer')
router.register(r'batches',        StockBatchViewSet,    basename='batch')

urlpatterns = router.urls
