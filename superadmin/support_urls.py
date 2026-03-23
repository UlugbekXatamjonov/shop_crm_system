from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import StoreTicketViewSet

router = DefaultRouter()
router.register('tickets', StoreTicketViewSet, basename='store-tickets')

urlpatterns = [
    path('', include(router.urls)),
]
