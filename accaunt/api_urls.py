"""
============================================================
ACCAUNT APP — Worker API URL'lari
============================================================
Do'kon hodimlarini boshqarish uchun endpointlar.

Prefix: /api/v1/
Router avtomatik quyidagi URL'larni yaratadi:

  GET    /api/v1/workers/                  — hodimlar ro'yxati
  POST   /api/v1/workers/                  — yangi hodim qo'shish
  GET    /api/v1/workers/{id}/             — hodim ma'lumoti
  PATCH  /api/v1/workers/{id}/             — hodimni yangilash
  DELETE /api/v1/workers/{id}/             — hodimni o'chirish (deaktivatsiya)
  POST   /api/v1/workers/{id}/activate/    — hodimni faollashtirish
  POST   /api/v1/workers/{id}/deactivate/  — hodimni deaktivatsiya qilish
  PATCH  /api/v1/workers/{id}/permissions/ — individual permission o'zgartirish
"""

from rest_framework.routers import DefaultRouter
from .views import WorkerViewSet

router = DefaultRouter()
router.register(r'workers', WorkerViewSet, basename='worker')

urlpatterns = router.urls
