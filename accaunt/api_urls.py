"""
============================================================
ACCAUNT APP — Worker API URL'lari
============================================================
Do'kon hodimlarini boshqarish uchun endpointlar.

Prefix: /api/v1/
Router avtomatik quyidagi URL'larni yaratadi:

  GET    /api/v1/workers/      — hodimlar ro'yxati       (manager/seller ham)
  POST   /api/v1/workers/      — yangi hodim qo'shish    (faqat owner)
  GET    /api/v1/workers/{id}/ — hodim ma'lumoti         (manager/seller ham)
  PATCH  /api/v1/workers/{id}/ — hodimni yangilash       (faqat owner)
                                  user, worker, permissions bitta so'rovda
"""

from rest_framework.routers import DefaultRouter
from .views import WorkerViewSet

router = DefaultRouter()
router.register(r'workers', WorkerViewSet, basename='worker')

urlpatterns = router.urls
