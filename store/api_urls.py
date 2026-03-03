"""
============================================================
STORE APP — Do'kon, Filial, Sozlamalar va Smena API URL'lari
============================================================
Prefix: /api/v1/

Router avtomatik quyidagi URL'larni yaratadi:

  GET    /api/v1/stores/           — do'konlar ro'yxati
  POST   /api/v1/stores/           — yangi do'kon yaratish
  GET    /api/v1/stores/{id}/      — do'kon tafsilotlari
  PATCH  /api/v1/stores/{id}/      — do'kon yangilash
  DELETE /api/v1/stores/{id}/      — do'konni nofaol qilish

  GET    /api/v1/branches/         — filiallar ro'yxati
  POST   /api/v1/branches/         — yangi filial yaratish
  GET    /api/v1/branches/{id}/    — filial tafsilotlari
  PATCH  /api/v1/branches/{id}/    — filial yangilash
  DELETE /api/v1/branches/{id}/    — filialni nofaol qilish

  GET    /api/v1/settings/         — do'kon sozlamalari (CanAccess('sozlamalar'))
  PATCH  /api/v1/settings/{id}/    — sozlamalarni yangilash (faqat owner)
  [create va delete YO'Q — signal avtomatik yaratadi]

  GET    /api/v1/shifts/               — smenalar ro'yxati (?status=open|closed, ?branch=id)
  POST   /api/v1/shifts/               — smena ochish
  GET    /api/v1/shifts/{id}/          — smena tafsilotlari
  PATCH  /api/v1/shifts/{id}/close/    — smena yopish (Z-report)
  GET    /api/v1/shifts/{id}/x-report/ — X-report (smena yopilmaydi)
  [delete YO'Q — smenalar o'chirilmaydi]
"""

from rest_framework.routers import DefaultRouter

from .views import BranchViewSet, SmenaViewSet, StoreSettingsViewSet, StoreViewSet

router = DefaultRouter()
router.register(r'stores',   StoreViewSet,         basename='store')
router.register(r'branches', BranchViewSet,        basename='branch')
router.register(r'settings', StoreSettingsViewSet, basename='store-settings')
router.register(r'shifts',   SmenaViewSet,         basename='smena')

urlpatterns = router.urls
