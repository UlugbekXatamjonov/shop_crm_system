"""
GET /api/v1/dashboard/
    ?date_from=YYYY-MM-DD
    ?date_to=YYYY-MM-DD
    ?branch=<id>
    ?limit=10
"""

from django.urls import path

from .views import DashboardView

urlpatterns = [
    path('', DashboardView.as_view(), name='dashboard'),
]
