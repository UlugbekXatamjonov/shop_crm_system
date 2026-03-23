from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AdminExpenseViewSet,
    ApplyCouponView,
    StoreMyReferralsView,
    StoreReferralView,
    StoreTicketViewSet,
    SuperAdminCouponViewSet,
    SuperAdminDashboardView,
    SuperAdminFinancialExportView,
    SuperAdminFinancialView,
    SuperAdminPlanViewSet,
    SuperAdminReferralStatsView,
    SuperAdminReferralView,
    SuperAdminStoreViewSet,
    SuperAdminSubscriptionViewSet,
    SuperAdminTicketViewSet,
    SuperAdminWorkerViewSet,
)

# Superadmin router
router = DefaultRouter()
router.register('stores',         SuperAdminStoreViewSet,        basename='superadmin-stores')
router.register('subscriptions',  SuperAdminSubscriptionViewSet, basename='superadmin-subscriptions')
router.register('coupons',        SuperAdminCouponViewSet,       basename='superadmin-coupons')
router.register('admin-expenses', AdminExpenseViewSet,           basename='superadmin-expenses')
router.register('plans',          SuperAdminPlanViewSet,         basename='superadmin-plans')
router.register('tickets',        SuperAdminTicketViewSet,       basename='superadmin-tickets')
router.register('workers',        SuperAdminWorkerViewSet,       basename='superadmin-workers')

urlpatterns = [
    # Dashboard va moliya
    path('dashboard/',        SuperAdminDashboardView.as_view(),      name='superadmin-dashboard'),
    path('financial/',        SuperAdminFinancialView.as_view(),       name='superadmin-financial'),
    path('financial/export/', SuperAdminFinancialExportView.as_view(), name='superadmin-financial-export'),

    # Referral (superadmin)
    path('referrals/',        SuperAdminReferralView.as_view(),        name='superadmin-referrals'),
    path('referrals/stats/',  SuperAdminReferralStatsView.as_view(),   name='superadmin-referrals-stats'),

    path('', include(router.urls)),
]
