"""
============================================================
ACCAUNT APP — Worker API URL'lari
============================================================
Do'kon hodimlarini boshqarish uchun endpointlar.

Prefix: /api/v1/
Router avtomatik quyidagi URL'larni yaratadi:

  GET    /api/v1/workers/                      — hodimlar ro'yxati       (manager+)
  POST   /api/v1/workers/                      — yangi hodim qo'shish    (faqat owner)
  GET    /api/v1/workers/me/                   — o'z profilini ko'rish   (barcha rollar)
  PATCH  /api/v1/workers/me/                   — email, phone1, phone2, parol
  GET    /api/v1/workers/{id}/                 — hodim ma'lumoti         (manager+)
  PATCH  /api/v1/workers/{id}/                 — hodimni yangilash       (faqat owner)
  GET    /api/v1/workers/{id}/kpi/             — xodim KPI tarixi        (manager+)
  GET    /api/v1/workers/{id}/kpi/?month=3&year=2026

  GET    /api/v1/kpi/                          — barcha xodimlar KPI     (manager+)
  GET    /api/v1/kpi/{id}/                     — bitta KPI yozuvi
  PATCH  /api/v1/kpi/{id}/set-target/          — maqsad va bonus belgilash
  GET    /api/v1/kpi/?month=3&year=2026&worker=<id>
"""

from rest_framework.routers import DefaultRouter
from .views import WorkerViewSet, WorkerKPIViewSet, AuditLogViewSet

router = DefaultRouter()
router.register(r'workers',    WorkerViewSet,    basename='worker')
router.register(r'kpi',        WorkerKPIViewSet, basename='kpi')
router.register(r'audit-logs', AuditLogViewSet,  basename='audit-log')

urlpatterns = router.urls
