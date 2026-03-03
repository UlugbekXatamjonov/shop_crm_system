"""
============================================================
TRADE APP — Mijozlar va Sotuvlar API URL'lari
============================================================
Prefix: /api/v1/

Router avtomatik quyidagi URL'larni yaratadi:

  GET    /api/v1/customer-groups/         — mijoz guruhlari ro'yxati
  POST   /api/v1/customer-groups/         — yangi guruh yaratish (IsManagerOrAbove)
  GET    /api/v1/customer-groups/{id}/    — guruh tafsilotlari
  PATCH  /api/v1/customer-groups/{id}/    — guruh yangilash (IsManagerOrAbove)
  DELETE /api/v1/customer-groups/{id}/    — guruh o'chirish (IsManagerOrAbove)

  GET    /api/v1/customers/               — mijozlar ro'yxati (?status=active|inactive, ?group=id, ?search=)
  POST   /api/v1/customers/               — yangi mijoz yaratish (CanAccess('sotuv'))
  GET    /api/v1/customers/{id}/          — mijoz tafsilotlari
  PATCH  /api/v1/customers/{id}/          — mijoz yangilash
  DELETE /api/v1/customers/{id}/          — mijozni nofaol qilish (soft delete)

  GET    /api/v1/sales/                   — sotuvlar ro'yxati (?status=completed|cancelled, ?branch=id, ?smena=id)
  POST   /api/v1/sales/                   — yangi sotuv yaratish (@transaction.atomic, CanAccess('sotuv'))
  GET    /api/v1/sales/{id}/              — sotuv tafsilotlari
  PATCH  /api/v1/sales/{id}/cancel/       — sotuvni bekor qilish (@transaction.atomic)
  [PUT, DELETE YO'Q — sotuvlar o'chirilmaydi]
"""

from rest_framework.routers import DefaultRouter

from .views import CustomerGroupViewSet, CustomerViewSet, SaleViewSet

router = DefaultRouter()
router.register(r'customer-groups', CustomerGroupViewSet, basename='customer-group')
router.register(r'customers',       CustomerViewSet,      basename='customer')
router.register(r'sales',           SaleViewSet,          basename='sale')

urlpatterns = router.urls
