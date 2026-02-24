"""
============================================================
STORE APP — Do'kon va Filial API URL'lari
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
"""

from rest_framework.routers import DefaultRouter

from .views import BranchViewSet, StoreViewSet

router = DefaultRouter()
router.register(r'stores',   StoreViewSet,  basename='store')
router.register(r'branches', BranchViewSet, basename='branch')

urlpatterns = router.urls
