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

  GET    /api/v1/warehouse/products/             — mahsulotlar ro'yxati
  POST   /api/v1/warehouse/products/             — mahsulot yaratish
  GET    /api/v1/warehouse/products/{id}/        — mahsulot tafsilotlari
  PATCH  /api/v1/warehouse/products/{id}/        — mahsulot yangilash
  DELETE /api/v1/warehouse/products/{id}/        — mahsulotni nofaol qilish

  GET    /api/v1/warehouse/warehouses/           — omborlar ro'yxati
  POST   /api/v1/warehouse/warehouses/           — ombor yaratish (owner)
  GET    /api/v1/warehouse/warehouses/{id}/      — ombor tafsilotlari
  PATCH  /api/v1/warehouse/warehouses/{id}/      — omborni yangilash
  DELETE /api/v1/warehouse/warehouses/{id}/      — omborni nofaol qilish (owner)

  GET    /api/v1/warehouse/stocks/               — qoldiqlar ro'yxati
  POST   /api/v1/warehouse/stocks/               — qoldiq qo'shish
  GET    /api/v1/warehouse/stocks/{id}/          — qoldiq tafsilotlari
  PATCH  /api/v1/warehouse/stocks/{id}/          — qoldiqni yangilash
  DELETE /api/v1/warehouse/stocks/{id}/          — qoldiqni o'chirish

  GET    /api/v1/warehouse/movements/            — harakatlar ro'yxati
  POST   /api/v1/warehouse/movements/            — harakat yaratish (kirim/chiqim/ko'chirish)
  GET    /api/v1/warehouse/movements/{id}/       — harakat tafsilotlari
"""

from rest_framework.routers import DefaultRouter

from .views import (
    CategoryViewSet,
    ProductViewSet,
    StockMovementViewSet,
    StockViewSet,
    WarehouseViewSet,
)

router = DefaultRouter()
router.register(r'categories', CategoryViewSet,      basename='category')
router.register(r'products',   ProductViewSet,       basename='product')
router.register(r'warehouses', WarehouseViewSet,     basename='warehouse')
router.register(r'stocks',     StockViewSet,         basename='stock')
router.register(r'movements',  StockMovementViewSet, basename='movement')

urlpatterns = router.urls
