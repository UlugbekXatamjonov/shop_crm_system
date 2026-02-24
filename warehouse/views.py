"""
============================================================
WAREHOUSE APP — View'lar
============================================================
ViewSet'lar:
  CategoryViewSet      — Kategoriyalarni boshqarish
  ProductViewSet       — Mahsulotlarni boshqarish
  StockViewSet         — Ombor qoldiqlarini boshqarish
  StockMovementViewSet — Kirim/chiqim harakatlarini boshqarish

Ruxsatlar:
  list/retrieve → CanAccess('mahsulotlar') yoki CanAccess('sklad')
  create/update/destroy → IsManagerOrAbove

StockMovement:
  Harakatlar faqat POST (create) bilan yaratiladi.
  UPDATE va DELETE yo'q — harakatlar immutable.
  Yaratishda Stock qoldig'i avtomatik yangilanadi.
"""

from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accaunt.models import AuditLog
from accaunt.permissions import CanAccess, IsManagerOrAbove

from .models import (
    Category,
    MovementType,
    Product,
    ProductStatus,
    Stock,
    StockMovement,
)
from .serializers import (
    CategoryCreateSerializer,
    CategoryDetailSerializer,
    CategoryListSerializer,
    CategoryUpdateSerializer,
    MovementCreateSerializer,
    MovementDetailSerializer,
    MovementListSerializer,
    ProductCreateSerializer,
    ProductDetailSerializer,
    ProductListSerializer,
    ProductUpdateSerializer,
    StockCreateSerializer,
    StockDetailSerializer,
    StockListSerializer,
    StockUpdateSerializer,
)


# ============================================================
# KATEGORIYA VIEWSET
# ============================================================

class CategoryViewSet(viewsets.ModelViewSet):
    """
    Kategoriyalarni boshqarish.

    Endpointlar:
      GET    /api/v1/warehouse/categories/       — ro'yxat
      POST   /api/v1/warehouse/categories/       — yaratish (manager+)
      GET    /api/v1/warehouse/categories/{id}/  — tafsilotlar
      PATCH  /api/v1/warehouse/categories/{id}/  — yangilash (manager+)
      DELETE /api/v1/warehouse/categories/{id}/  — nofaol qilish (manager+, soft delete)

    Multi-tenant:
      Foydalanuvchi faqat o'z do'konining kategoriyalarini ko'radi.
    """
    http_method_names = ['get', 'post', 'patch', 'delete']

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated(), CanAccess('mahsulotlar')]
        return [IsAuthenticated(), IsManagerOrAbove()]

    def get_serializer_class(self):
        if self.action == 'list':
            return CategoryListSerializer
        if self.action == 'create':
            return CategoryCreateSerializer
        if self.action in ('update', 'partial_update'):
            return CategoryUpdateSerializer
        return CategoryDetailSerializer

    def get_queryset(self):
        worker = getattr(self.request.user, 'worker', None)
        if not worker or not worker.store:
            return Category.objects.none()
        return Category.objects.filter(store=worker.store)

    def get_serializer_context(self):
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
            target_model='Category',
            target_id=instance.id,
            description=f"Kategoriya yaratildi: '{instance.name}'",
        )

    def perform_update(self, serializer):
        instance = serializer.save()
        AuditLog.objects.create(
            actor=self.request.user,
            action=AuditLog.Action.UPDATE,
            target_model='Category',
            target_id=instance.id,
            description=f"Kategoriya yangilandi: '{instance.name}'",
        )

    def perform_destroy(self, instance: Category):
        """Soft delete — o'chirish o'rniga status='inactive' ga o'tkaziladi."""
        instance.status = ProductStatus.INACTIVE
        instance.save(update_fields=['status'])
        AuditLog.objects.create(
            actor=self.request.user,
            action=AuditLog.Action.DELETE,
            target_model='Category',
            target_id=instance.id,
            description=f"Kategoriya nofaol qilindi: '{instance.name}'",
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            {
                'message': "Kategoriya muvaffaqiyatli yaratildi.",
                'data': CategoryDetailSerializer(
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
                'message': "Kategoriya muvaffaqiyatli yangilandi.",
                'data': CategoryDetailSerializer(
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
            {'message': "Kategoriya muvaffaqiyatli nofaol qilindi."},
            status=status.HTTP_200_OK,
        )


# ============================================================
# MAHSULOT VIEWSET
# ============================================================

class ProductViewSet(viewsets.ModelViewSet):
    """
    Mahsulotlarni boshqarish.

    Endpointlar:
      GET    /api/v1/warehouse/products/       — ro'yxat
      POST   /api/v1/warehouse/products/       — yaratish (manager+)
      GET    /api/v1/warehouse/products/{id}/  — tafsilotlar
      PATCH  /api/v1/warehouse/products/{id}/  — yangilash (manager+)
      DELETE /api/v1/warehouse/products/{id}/  — nofaol qilish (manager+, soft delete)

    Multi-tenant:
      Foydalanuvchi faqat o'z do'konining mahsulotlarini ko'radi.
    """
    http_method_names = ['get', 'post', 'patch', 'delete']

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated(), CanAccess('mahsulotlar')]
        return [IsAuthenticated(), IsManagerOrAbove()]

    def get_serializer_class(self):
        if self.action == 'list':
            return ProductListSerializer
        if self.action == 'create':
            return ProductCreateSerializer
        if self.action in ('update', 'partial_update'):
            return ProductUpdateSerializer
        return ProductDetailSerializer

    def get_queryset(self):
        worker = getattr(self.request.user, 'worker', None)
        if not worker or not worker.store:
            return Product.objects.none()
        return (
            Product.objects
            .filter(store=worker.store)
            .select_related('category', 'store')
        )

    def get_serializer_context(self):
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
            target_model='Product',
            target_id=instance.id,
            description=f"Mahsulot yaratildi: '{instance.name}'",
        )

    def perform_update(self, serializer):
        instance = serializer.save()
        AuditLog.objects.create(
            actor=self.request.user,
            action=AuditLog.Action.UPDATE,
            target_model='Product',
            target_id=instance.id,
            description=f"Mahsulot yangilandi: '{instance.name}'",
        )

    def perform_destroy(self, instance: Product):
        """Soft delete — o'chirish o'rniga status='inactive' ga o'tkaziladi."""
        instance.status = ProductStatus.INACTIVE
        instance.save(update_fields=['status'])
        AuditLog.objects.create(
            actor=self.request.user,
            action=AuditLog.Action.DELETE,
            target_model='Product',
            target_id=instance.id,
            description=f"Mahsulot nofaol qilindi: '{instance.name}'",
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            {
                'message': "Mahsulot muvaffaqiyatli yaratildi.",
                'data': ProductDetailSerializer(
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
                'message': "Mahsulot muvaffaqiyatli yangilandi.",
                'data': ProductDetailSerializer(
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
            {'message': "Mahsulot muvaffaqiyatli nofaol qilindi."},
            status=status.HTTP_200_OK,
        )


# ============================================================
# OMBOR QOLDIG'I VIEWSET
# ============================================================

class StockViewSet(viewsets.ModelViewSet):
    """
    Ombor qoldiqlarini boshqarish.

    Endpointlar:
      GET    /api/v1/warehouse/stocks/       — ro'yxat
      POST   /api/v1/warehouse/stocks/       — qo'lda qo'shish (manager+)
      GET    /api/v1/warehouse/stocks/{id}/  — tafsilotlar
      PATCH  /api/v1/warehouse/stocks/{id}/  — miqdorni yangilash (manager+)
      DELETE /api/v1/warehouse/stocks/{id}/  — o'chirish (manager+, hard delete)

    Odatda StockMovement POST qilganda Stock avtomatik yaratiladi/yangilanadi.
    Bu viewset bevosita qoldiq kiritish uchun (boshlang'ich inventarizatsiya).
    """
    http_method_names = ['get', 'post', 'patch', 'delete']

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated(), CanAccess('sklad')]
        return [IsAuthenticated(), IsManagerOrAbove()]

    def get_serializer_class(self):
        if self.action == 'list':
            return StockListSerializer
        if self.action == 'create':
            return StockCreateSerializer
        if self.action in ('update', 'partial_update'):
            return StockUpdateSerializer
        return StockDetailSerializer

    def get_queryset(self):
        worker = getattr(self.request.user, 'worker', None)
        if not worker or not worker.store:
            return Stock.objects.none()
        return (
            Stock.objects
            .filter(product__store=worker.store)
            .select_related('product', 'branch')
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        worker = getattr(self.request.user, 'worker', None)
        if worker:
            context['store'] = worker.store
        return context

    def perform_create(self, serializer):
        instance = serializer.save()
        AuditLog.objects.create(
            actor=self.request.user,
            action=AuditLog.Action.CREATE,
            target_model='Stock',
            target_id=instance.id,
            description=(
                f"Ombor qoldig'i qo'shildi: '{instance.product.name}' "
                f"({instance.branch.name}) = {instance.quantity}"
            ),
        )

    def perform_update(self, serializer):
        instance = serializer.save()
        AuditLog.objects.create(
            actor=self.request.user,
            action=AuditLog.Action.UPDATE,
            target_model='Stock',
            target_id=instance.id,
            description=(
                f"Ombor qoldig'i yangilandi: '{instance.product.name}' "
                f"({instance.branch.name}) = {instance.quantity}"
            ),
        )

    def perform_destroy(self, instance: Stock):
        pk   = instance.id
        name = f"{instance.product.name} ({instance.branch.name})"
        instance.delete()
        AuditLog.objects.create(
            actor=self.request.user,
            action=AuditLog.Action.DELETE,
            target_model='Stock',
            target_id=pk,
            description=f"Ombor qoldig'i o'chirildi: '{name}'",
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            {
                'message': "Ombor qoldig'i muvaffaqiyatli qo'shildi.",
                'data': StockDetailSerializer(serializer.instance).data,
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
                'message': "Ombor qoldig'i muvaffaqiyatli yangilandi.",
                'data': StockDetailSerializer(serializer.instance).data,
            },
            status=status.HTTP_200_OK,
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(
            {'message': "Ombor qoldig'i muvaffaqiyatli o'chirildi."},
            status=status.HTTP_200_OK,
        )


# ============================================================
# HARAKAT (KIRIM/CHIQIM) VIEWSET
# ============================================================

class StockMovementViewSet(viewsets.ModelViewSet):
    """
    Mahsulot kirim/chiqim harakatlarini boshqarish.

    Endpointlar:
      GET    /api/v1/warehouse/movements/       — ro'yxat
      POST   /api/v1/warehouse/movements/       — yangi harakat
      GET    /api/v1/warehouse/movements/{id}/  — tafsilotlar

    Muhim:
      Harakatlar o'zgartirilmaydi va o'chirilmaydi (immutable log).
      Xatolikni tuzatish uchun qarama-qarshi harakat yarating.

    Yaratishda:
      - Chiqim uchun qoldiq yetarliligi tekshiriladi (serializer)
      - Stock.quantity avtomatik yangilanadi (perform_create)
    """
    http_method_names = ['get', 'post']

    def get_permissions(self):
        return [IsAuthenticated(), CanAccess('sklad')]

    def get_serializer_class(self):
        if self.action == 'list':
            return MovementListSerializer
        if self.action == 'create':
            return MovementCreateSerializer
        return MovementDetailSerializer

    def get_queryset(self):
        worker = getattr(self.request.user, 'worker', None)
        if not worker or not worker.store:
            return StockMovement.objects.none()
        return (
            StockMovement.objects
            .filter(product__store=worker.store)
            .select_related('product', 'branch', 'worker__user')
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        worker = getattr(self.request.user, 'worker', None)
        if worker:
            context['store'] = worker.store
        return context

    def perform_create(self, serializer):
        worker   = getattr(self.request.user, 'worker', None)
        instance = serializer.save(worker=worker)

        # Stock qoldig'ini yangilash
        stock, _ = Stock.objects.get_or_create(
            product=instance.product,
            branch=instance.branch,
            defaults={'quantity': 0},
        )
        if instance.movement_type == MovementType.IN:
            stock.quantity += instance.quantity
        else:
            stock.quantity -= instance.quantity
        stock.save(update_fields=['quantity', 'updated_on'])

        AuditLog.objects.create(
            actor=self.request.user,
            action=AuditLog.Action.CREATE,
            target_model='StockMovement',
            target_id=instance.id,
            description=(
                f"{instance.get_movement_type_display()}: "
                f"'{instance.product.name}' × {instance.quantity} "
                f"({instance.branch.name})"
            ),
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            {
                'message': "Harakat muvaffaqiyatli qayd etildi.",
                'data': MovementDetailSerializer(
                    serializer.instance,
                    context=self.get_serializer_context(),
                ).data,
            },
            status=status.HTTP_201_CREATED,
        )
