"""
============================================================
STORE APP — View'lar
============================================================
ViewSet'lar:
  StoreViewSet  — Do'konni boshqarish (faqat egasi uchun)
  BranchViewSet — Filiallarni boshqarish

Multi-tenant xavfsizlik:
  Har bir foydalanuvchi faqat o'z do'konining
  ma'lumotlarini ko'ra va boshqara oladi.
"""

from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accaunt.models import AuditLog
from accaunt.permissions import CanAccess, IsOwner

from .models import Branch, Store, StoreStatus
from .serializers import (
    BranchCreateSerializer,
    BranchDetailSerializer,
    BranchListSerializer,
    BranchUpdateSerializer,
    StoreCreateSerializer,
    StoreDetailSerializer,
    StoreListSerializer,
    StoreUpdateSerializer,
)


# ============================================================
# DO'KON VIEWSET
# ============================================================

class StoreViewSet(viewsets.ModelViewSet):
    """
    Do'konni boshqarish.

    Endpointlar:
      GET    /api/v1/stores/       — o'z do'konini ko'rish (dokonlar ruxsati kerak)
      POST   /api/v1/stores/       — yangi do'kon yaratish (faqat owner)
      GET    /api/v1/stores/{id}/  — do'kon tafsilotlari (dokonlar ruxsati kerak)
      PATCH  /api/v1/stores/{id}/  — do'kon ma'lumotlarini yangilash (faqat owner)
      DELETE /api/v1/stores/{id}/  — do'konni nofaol qilish (faqat owner, soft delete)

    Multi-tenant:
      Owner faqat o'z do'konini ko'radi va boshqaradi.
    """
    http_method_names = ['get', 'post', 'patch', 'delete']

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated(), CanAccess('dokonlar')]
        return [IsAuthenticated(), IsOwner()]

    def get_serializer_class(self):
        if self.action == 'list':
            return StoreListSerializer
        if self.action == 'create':
            return StoreCreateSerializer
        if self.action in ('update', 'partial_update'):
            return StoreUpdateSerializer
        return StoreDetailSerializer

    def get_queryset(self):
        worker = getattr(self.request.user, 'worker', None)
        if not worker or not worker.store:
            return Store.objects.none()
        return Store.objects.filter(id=worker.store.id)

    def perform_create(self, serializer):
        instance = serializer.save()
        AuditLog.objects.create(
            actor=self.request.user,
            action=AuditLog.Action.CREATE,
            target_model='Store',
            target_id=instance.id,
            description=f"Do'kon yaratildi: '{instance.name}'",
        )

    def perform_update(self, serializer):
        instance = serializer.save()
        AuditLog.objects.create(
            actor=self.request.user,
            action=AuditLog.Action.UPDATE,
            target_model='Store',
            target_id=instance.id,
            description=f"Do'kon yangilandi: '{instance.name}'",
        )

    def perform_destroy(self, instance: Store):
        """Soft delete — o'chirish o'rniga status='inactive' ga o'tkaziladi."""
        instance.status = StoreStatus.INACTIVE
        instance.save(update_fields=['status'])
        AuditLog.objects.create(
            actor=self.request.user,
            action=AuditLog.Action.DELETE,
            target_model='Store',
            target_id=instance.id,
            description=f"Do'kon nofaol qilindi: '{instance.name}'",
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            {
                'message': "Do'kon muvaffaqiyatli yaratildi.",
                'data': StoreDetailSerializer(serializer.instance).data,
            },
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(
            {
                'message': "Do'kon muvaffaqiyatli yangilandi.",
                'data': StoreDetailSerializer(serializer.instance).data,
            },
            status=status.HTTP_200_OK,
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(
            {'message': "Do'kon muvaffaqiyatli nofaol qilindi."},
            status=status.HTTP_200_OK,
        )


# ============================================================
# FILIAL VIEWSET
# ============================================================

class BranchViewSet(viewsets.ModelViewSet):
    """
    Filiallarni boshqarish.

    Endpointlar:
      GET    /api/v1/branches/       — do'kning barcha filiallari
      POST   /api/v1/branches/       — yangi filial yaratish (faqat owner)
      GET    /api/v1/branches/{id}/  — filial tafsilotlari
      PATCH  /api/v1/branches/{id}/  — filial ma'lumotlarini yangilash (faqat owner)
      DELETE /api/v1/branches/{id}/  — filialni nofaol qilish (faqat owner, soft delete)

    Multi-tenant:
      Faqat o'z do'konining filiallarini ko'radi va boshqaradi.
    """
    http_method_names = ['get', 'post', 'patch', 'delete']

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsOwner()]

    def get_serializer_class(self):
        if self.action == 'list':
            return BranchListSerializer
        if self.action == 'create':
            return BranchCreateSerializer
        if self.action in ('update', 'partial_update'):
            return BranchUpdateSerializer
        return BranchDetailSerializer

    def get_queryset(self):
        worker = getattr(self.request.user, 'worker', None)
        if not worker or not worker.store:
            return Branch.objects.none()
        return (
            Branch.objects
            .filter(store=worker.store)
            .select_related('store')
        )

    def get_serializer_context(self):
        """store kontekstini serializer ga uzatish (BranchCreate validatsiyasi uchun)."""
        context = super().get_serializer_context()
        worker = getattr(self.request.user, 'worker', None)
        if worker:
            context['store'] = worker.store
        return context

    def perform_create(self, serializer):
        worker = self.request.user.worker
        instance = serializer.save(store=worker.store)
        AuditLog.objects.create(
            actor=self.request.user,
            action=AuditLog.Action.CREATE,
            target_model='Branch',
            target_id=instance.id,
            description=f"Filial yaratildi: '{instance.name}'",
        )

    def perform_update(self, serializer):
        instance = serializer.save()
        AuditLog.objects.create(
            actor=self.request.user,
            action=AuditLog.Action.UPDATE,
            target_model='Branch',
            target_id=instance.id,
            description=f"Filial yangilandi: '{instance.name}'",
        )

    def perform_destroy(self, instance: Branch):
        """Soft delete — o'chirish o'rniga status='inactive' ga o'tkaziladi."""
        instance.status = StoreStatus.INACTIVE
        instance.save(update_fields=['status'])
        AuditLog.objects.create(
            actor=self.request.user,
            action=AuditLog.Action.DELETE,
            target_model='Branch',
            target_id=instance.id,
            description=f"Filial nofaol qilindi: '{instance.name}'",
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            {
                'message': "Filial muvaffaqiyatli yaratildi.",
                'data': BranchDetailSerializer(
                    serializer.instance,
                    context=self.get_serializer_context(),
                ).data,
            },
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(
            {
                'message': "Filial muvaffaqiyatli yangilandi.",
                'data': BranchDetailSerializer(
                    serializer.instance,
                    context=self.get_serializer_context(),
                ).data,
            },
            status=status.HTTP_200_OK,
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(
            {'message': "Filial muvaffaqiyatli nofaol qilindi."},
            status=status.HTTP_200_OK,
        )
