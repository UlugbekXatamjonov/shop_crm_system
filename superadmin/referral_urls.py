from django.urls import path

from .views import StoreMyReferralsView, StoreReferralView

urlpatterns = [
    path('my-code/',     StoreReferralView.as_view(),      name='referral-my-code'),
    path('my-referrals/', StoreMyReferralsView.as_view(),  name='referral-my-referrals'),
]
