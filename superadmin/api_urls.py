from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AdminExpenseViewSet,
    ApplyCouponView,
    SuperAdminCouponViewSet,
    SuperAdminDashboardView,
    SuperAdminFinancialExportView,
    SuperAdminFinancialView,
    SuperAdminPlanViewSet,
    SuperAdminStoreViewSet,
    SuperAdminSubscriptionViewSet,
)

router = DefaultRouter()
router.register('stores',        SuperAdminStoreViewSet,        basename='superadmin-stores')
router.register('subscriptions', SuperAdminSubscriptionViewSet, basename='superadmin-subscriptions')
router.register('coupons',       SuperAdminCouponViewSet,       basename='superadmin-coupons')
router.register('admin-expenses', AdminExpenseViewSet,          basename='superadmin-expenses')
router.register('plans',         SuperAdminPlanViewSet,         basename='superadmin-plans')

urlpatterns = [
    path('dashboard/',          SuperAdminDashboardView.as_view(),      name='superadmin-dashboard'),
    path('financial/',          SuperAdminFinancialView.as_view(),       name='superadmin-financial'),
    path('financial/export/',   SuperAdminFinancialExportView.as_view(), name='superadmin-financial-export'),
    path('', include(router.urls)),
]
