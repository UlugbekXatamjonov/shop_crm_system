"""
============================================================
EXPENSE APP — View'lar
============================================================
ViewSet'lar:
  ExpenseCategoryViewSet — Xarajat kategoriyalari CRUD (soft delete)
  ExpenseViewSet         — Xarajatlar CRUD (hard delete, IsManagerOrAbove)

Ruxsatlar:
  list/retrieve  → CanAccess('xarajatlar')
  create/update  → CanAccess('xarajatlar')
  delete         → IsManagerOrAbove
"""

from django.utils import timezone

from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accaunt.audit_mixin import AuditMixin
from accaunt.models import AuditLog
from accaunt.permissions import CanAccess, IsManagerOrAbove

from store.models import Smena, SmenaStatus

from config.cache_utils import get_store_settings

from .models import Expense, ExpenseCategory
from .serializers import (
    ExpenseCategoryCreateSerializer,
    ExpenseCategoryDetailSerializer,
    ExpenseCategoryListSerializer,
    ExpenseCategoryUpdateSerializer,
    ExpenseCreateSerializer,
    ExpenseDetailSerializer,
    ExpenseListSerializer,
    ExpenseUpdateSerializer,
)


# ============================================================
# XARAJAT KATEGORIYASI VIEWSET
# ============================================================

class ExpenseCategoryViewSet(AuditMixin, viewsets.ModelViewSet):
    """
    Xarajat kategoriyalarini boshqarish.
    Soft delete — status='inactive' ga o'tkaziladi.

    GET    /api/v1/expense-categories/         — ro'yxat (?status=active|inactive)
    POST   /api/v1/expense-categories/         — yangi kategoriya (IsManagerOrAbove)
    GET    /api/v1/expense-categories/{id}/    — tafsilotlari
    PATCH  /api/v1/expense-categories/{id}/    — yangilash (IsManagerOrAbove)
    DELETE /api/v1/expense-categories/{id}/    — o'chirish (IsManagerOrAbove, soft)
    """
    http_method_names = ['get', 'post', 'patch', 'delete']

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsAuthenticated(), IsManagerOrAbove()]
        return [IsAuthenticated(), CanAccess('xarajatlar')]

    def get_queryset(self):
        worker = self.request.user.worker
        qs = ExpenseCategory.objects.filter(store=worker.store)

        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)

        return qs

    def get_serializer_class(self):
        if self.action == 'list':
            return ExpenseCategoryListSerializer
        if self.action == 'create':
            return ExpenseCategoryCreateSerializer
        if self.action in ('update', 'partial_update'):
            return ExpenseCategoryUpdateSerializer
        return ExpenseCategoryDetailSerializer

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        worker = getattr(self.request.user, 'worker', None)
        if worker:
            ctx['store'] = worker.store
        return ctx

    def perform_create(self, serializer):
        worker   = self.request.user.worker
        instance = serializer.save(store=worker.store)
        self._audit_log(AuditLog.Action.CREATE, instance,
                        description=f"Xarajat kategoriyasi yaratildi: '{instance.name}'")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        instance = ExpenseCategory.objects.get(
            store=request.user.worker.store,
            name=serializer.validated_data['name'],
        )
        return Response(
            {
                'message': "Xarajat kategoriyasi muvaffaqiyatli yaratildi.",
                'data': ExpenseCategoryDetailSerializer(instance).data,
            },
            status=status.HTTP_201_CREATED,
        )

    def perform_update(self, serializer):
        instance = serializer.save()
        self._audit_log(AuditLog.Action.UPDATE, instance,
                        description=f"Xarajat kategoriyasi yangilandi: '{instance.name}'")

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', True)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        instance.refresh_from_db()
        return Response(
            {
                'message': "Xarajat kategoriyasi yangilandi.",
                'data': ExpenseCategoryDetailSerializer(instance).data,
            },
            status=status.HTTP_200_OK,
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.status = 'inactive'
        instance.save(update_fields=['status'])
        self._audit_log(AuditLog.Action.DELETE, instance,
                        description=f"Xarajat kategoriyasi nofaol qilindi: '{instance.name}'")
        return Response(
            {'message': "Xarajat kategoriyasi nofaol qilindi."},
            status=status.HTTP_200_OK,
        )


# ============================================================
# XARAJAT VIEWSET
# ============================================================

class ExpenseViewSet(AuditMixin, viewsets.ModelViewSet):
    """
    Xarajatlarni boshqarish.
    Hard delete — xarajat to'liq o'chiriladi (faqat manager+).

    GET    /api/v1/expenses/         — ro'yxat (?branch=id, ?category=id, ?smena=id, ?date=YYYY-MM-DD)
    POST   /api/v1/expenses/         — yangi xarajat
    GET    /api/v1/expenses/{id}/    — tafsilotlari
    PATCH  /api/v1/expenses/{id}/    — yangilash (IsManagerOrAbove)
    DELETE /api/v1/expenses/{id}/    — o'chirish (IsManagerOrAbove, hard)
    """
    http_method_names = ['get', 'post', 'patch', 'delete']

    def get_permissions(self):
        if self.action in ('update', 'partial_update', 'destroy'):
            return [IsAuthenticated(), IsManagerOrAbove()]
        return [IsAuthenticated(), CanAccess('xarajatlar')]

    def get_queryset(self):
        worker = self.request.user.worker
        qs = Expense.objects.filter(
            store=worker.store,
        ).select_related(
            'category', 'branch', 'worker__user', 'smena',
        )

        branch_filter = self.request.query_params.get('branch')
        if branch_filter:
            qs = qs.filter(branch_id=branch_filter)

        category_filter = self.request.query_params.get('category')
        if category_filter:
            qs = qs.filter(category_id=category_filter)

        smena_filter = self.request.query_params.get('smena')
        if smena_filter:
            qs = qs.filter(smena_id=smena_filter)

        date_filter = self.request.query_params.get('date')
        if date_filter:
            qs = qs.filter(date=date_filter)

        return qs

    def get_serializer_class(self):
        if self.action == 'list':
            return ExpenseListSerializer
        if self.action == 'create':
            return ExpenseCreateSerializer
        if self.action in ('update', 'partial_update'):
            return ExpenseUpdateSerializer
        return ExpenseDetailSerializer

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        return ctx

    def perform_create(self, serializer):
        worker   = self.request.user.worker
        settings = get_store_settings(worker.store_id)

        # Ochiq smenani topish (shift yoqilgan bo'lsa)
        current_smena = None
        branch = serializer.validated_data.get('branch')
        if settings.shift_enabled and branch:
            current_smena = Smena.objects.filter(
                branch=branch,
                status=SmenaStatus.OPEN,
            ).first()

        instance = serializer.save(
            store=worker.store,
            worker=worker,
            smena=current_smena,
        )
        self._audit_log(
            AuditLog.Action.CREATE,
            instance,
            description=(
                f"Xarajat qayd etildi: '{instance.category.name}', "
                f"{instance.amount} so'm, {instance.date}"
            ),
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        instance = Expense.objects.select_related(
            'category', 'branch', 'worker__user', 'smena',
        ).filter(
            store=request.user.worker.store,
        ).latest('created_on')
        return Response(
            {
                'message': "Xarajat muvaffaqiyatli qayd etildi.",
                'data': ExpenseDetailSerializer(instance).data,
            },
            status=status.HTTP_201_CREATED,
        )

    def perform_update(self, serializer):
        instance = serializer.save()
        self._audit_log(AuditLog.Action.UPDATE, instance,
                        description=f"Xarajat yangilandi: #{instance.id}")

    def update(self, request, *args, **kwargs):
        partial  = kwargs.pop('partial', True)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        instance.refresh_from_db()
        return Response(
            {
                'message': "Xarajat yangilandi.",
                'data': ExpenseDetailSerializer(
                    instance,
                    context=self.get_serializer_context(),
                ).data,
            },
            status=status.HTTP_200_OK,
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        expense_id    = instance.id
        category_name = instance.category.name
        self._audit_log(AuditLog.Action.DELETE, instance,
                        description=f"Xarajat o'chirildi: #{expense_id} ({category_name})")
        instance.delete()
        return Response(
            {'message': "Xarajat o'chirildi."},
            status=status.HTTP_200_OK,
        )
