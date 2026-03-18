"""
============================================================
SUBSCRIPTION — URL'lar
============================================================
DO'KON EGASI:
  GET  /api/v1/subscription/             — joriy obuna holati
  GET  /api/v1/subscription/plans/       — barcha tarif rejalari
  GET  /api/v1/subscription/invoices/    — to'lov tarixi

SUPERADMIN:
  GET    /api/v1/admin/subscriptions/                      — ro'yxat (?status= ?plan_type=)
  GET    /api/v1/admin/subscriptions/{id}/                 — bitta
  PATCH  /api/v1/admin/subscriptions/{id}/                 — plan/status/sana o'zgartirish
  POST   /api/v1/admin/subscriptions/{id}/extend/          — muddat uzaytirish
  POST   /api/v1/admin/subscriptions/{id}/add-invoice/     — to'lov qo'shish
"""

from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    AdminSubscriptionViewSet,
    MyInvoiceListView,
    MySubscriptionView,
    PlanListView,
)

# Owner endpointlar
owner_urlpatterns = [
    path('subscription/',          MySubscriptionView.as_view(), name='my-subscription'),
    path('subscription/plans/',    PlanListView.as_view(),        name='subscription-plans'),
    path('subscription/invoices/', MyInvoiceListView.as_view(),   name='subscription-invoices'),
]

# SuperAdmin endpointlar
admin_router = DefaultRouter()
admin_router.register(
    r'admin/subscriptions',
    AdminSubscriptionViewSet,
    basename='admin-subscription',
)

urlpatterns = owner_urlpatterns + admin_router.urls
