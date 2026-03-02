"""
============================================================
WAREHOUSE APP — View'lar
============================================================
ViewSet'lar:
  CategoryViewSet      — Kategoriyalarni boshqarish
  ProductViewSet       — Mahsulotlarni boshqarish
  WarehouseViewSet     — Omborlarni boshqarish
  StockViewSet         — Qoldiqlarni boshqarish
  StockMovementViewSet — Kirim/chiqim/ko'chirish harakatlarini boshqarish

Ruxsatlar:
  list/retrieve → CanAccess('mahsulotlar') yoki CanAccess('ombor')
  create/update/destroy → IsManagerOrAbove

StockMovement:
  Harakatlar faqat POST (create) bilan yaratiladi.
  UPDATE va DELETE yo'q — harakatlar immutable.
  Yaratishda Stock qoldig'i avtomatik yangilanadi.
"""

from django.db.models import Case, IntegerField, Value, When

from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accaunt.models import AuditLog
from accaunt.permissions import CanAccess, IsManagerOrAbove, IsOwner

from .models import (
    Category,
    MovementType,
    Product,
    ProductStatus,
    Stock,
    StockMovement,
    Warehouse,
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
    WarehouseCreateSerializer,
    WarehouseDetailSerializer,
    WarehouseListSerializer,
    WarehouseUpdateSerializer,
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
      DELETE /api/v1/warehouse/categories/{id}/  — o'chirish (manager+, hard delete)

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
        return (
            Category.objects
            .filter(store=worker.store)
            .annotate(
                status_order=Case(
                    When(status='active',   then=Value(0)),
                    When(status='inactive', then=Value(1)),
                    default=Value(2),
                    output_field=IntegerField(),
                )
            )
            .order_by('status_order', 'name')
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
        pk   = instance.id
        name = instance.name
        instance.delete()
        AuditLog.objects.create(
            actor=self.request.user,
            action=AuditLog.Action.DELETE,
            target_model='Category',
            target_id=pk,
            description=f"Kategoriya o'chirildi: '{name}'",
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
            {'message': "Kategoriya muvaffaqiyatli o'chirildi."},
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
      DELETE /api/v1/warehouse/products/{id}/  — o'chirish (manager+, hard delete)

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
            .annotate(
                status_order=Case(
                    When(status='active',   then=Value(0)),
                    When(status='inactive', then=Value(1)),
                    default=Value(2),
                    output_field=IntegerField(),
                )
            )
            .order_by('status_order', 'name')
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
        pk   = instance.id
        name = instance.name
        instance.delete()
        AuditLog.objects.create(
            actor=self.request.user,
            action=AuditLog.Action.DELETE,
            target_model='Product',
            target_id=pk,
            description=f"Mahsulot o'chirildi: '{name}'",
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
            {'message': "Mahsulot muvaffaqiyatli o'chirildi."},
            status=status.HTTP_200_OK,
        )


# ============================================================
# OMBOR VIEWSET
# ============================================================

class WarehouseViewSet(viewsets.ModelViewSet):
    """
    Omborlarni boshqarish.

    Endpointlar:
      GET    /api/v1/warehouse/warehouses/       — ro'yxat
      POST   /api/v1/warehouse/warehouses/       — yaratish (owner)
      GET    /api/v1/warehouse/warehouses/{id}/  — tafsilotlar
      PATCH  /api/v1/warehouse/warehouses/{id}/  — yangilash (manager+)
      DELETE /api/v1/warehouse/warehouses/{id}/  — o'chirish (owner, hard delete)

    Multi-tenant:
      Foydalanuvchi faqat o'z do'konining omborlarini ko'radi.
    """
    http_method_names = ['get', 'post', 'patch', 'delete']

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated(), CanAccess('ombor')]
        if self.action in ('destroy', 'create'):
            return [IsAuthenticated(), IsOwner()]
        return [IsAuthenticated(), IsManagerOrAbove()]

    def get_serializer_class(self):
        if self.action == 'list':
            return WarehouseListSerializer
        if self.action == 'create':
            return WarehouseCreateSerializer
        if self.action in ('update', 'partial_update'):
            return WarehouseUpdateSerializer
        return WarehouseDetailSerializer

    def get_queryset(self):
        worker = getattr(self.request.user, 'worker', None)
        if not worker or not worker.store:
            return Warehouse.objects.none()
        return (
            Warehouse.objects
            .filter(store=worker.store)
            .annotate(
                status_order=Case(
                    When(status='active',   then=Value(0)),
                    When(status='inactive', then=Value(1)),
                    default=Value(2),
                    output_field=IntegerField(),
                )
            )
            .order_by('status_order', 'name')
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
            target_model='Warehouse',
            target_id=instance.id,
            description=f"Ombor yaratildi: '{instance.name}'",
        )

    def perform_update(self, serializer):
        instance = serializer.save()
        AuditLog.objects.create(
            actor=self.request.user,
            action=AuditLog.Action.UPDATE,
            target_model='Warehouse',
            target_id=instance.id,
            description=f"Ombor yangilandi: '{instance.name}'",
        )

    def perform_destroy(self, instance: Warehouse):
        pk   = instance.id
        name = instance.name
        instance.delete()
        AuditLog.objects.create(
            actor=self.request.user,
            action=AuditLog.Action.DELETE,
            target_model='Warehouse',
            target_id=pk,
            description=f"Ombor o'chirildi: '{name}'",
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            {
                'message': "Ombor muvaffaqiyatli yaratildi.",
                'data': WarehouseDetailSerializer(
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
                'message': "Ombor muvaffaqiyatli yangilandi.",
                'data': WarehouseDetailSerializer(
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
            {'message': "Ombor muvaffaqiyatli o'chirildi."},
            status=status.HTTP_200_OK,
        )


# ============================================================
# QOLDIQ VIEWSET
# ============================================================

class StockViewSet(viewsets.ModelViewSet):
    """
    Qoldiqlarni boshqarish (filial va ombor bo'yicha).

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
            return [IsAuthenticated(), CanAccess('ombor')]
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
            .select_related('product', 'branch', 'warehouse')
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        worker = getattr(self.request.user, 'worker', None)
        if worker:
            context['store'] = worker.store
        return context

    def perform_create(self, serializer):
        instance = serializer.save()
        location = instance.branch or instance.warehouse
        AuditLog.objects.create(
            actor=self.request.user,
            action=AuditLog.Action.CREATE,
            target_model='Stock',
            target_id=instance.id,
            description=(
                f"Qoldiq qo'shildi: '{instance.product.name}' "
                f"({location.name}) = {instance.quantity}"
            ),
        )

    def perform_update(self, serializer):
        instance = serializer.save()
        location = instance.branch or instance.warehouse
        AuditLog.objects.create(
            actor=self.request.user,
            action=AuditLog.Action.UPDATE,
            target_model='Stock',
            target_id=instance.id,
            description=(
                f"Qoldiq yangilandi: '{instance.product.name}' "
                f"({location.name}) = {instance.quantity}"
            ),
        )

    def perform_destroy(self, instance: Stock):
        pk       = instance.id
        location = instance.branch or instance.warehouse
        name     = f"{instance.product.name} ({location.name})"
        instance.delete()
        AuditLog.objects.create(
            actor=self.request.user,
            action=AuditLog.Action.DELETE,
            target_model='Stock',
            target_id=pk,
            description=f"Qoldiq o'chirildi: '{name}'",
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            {
                'message': "Qoldiq muvaffaqiyatli qo'shildi.",
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
                'message': "Qoldiq muvaffaqiyatli yangilandi.",
                'data': StockDetailSerializer(serializer.instance).data,
            },
            status=status.HTTP_200_OK,
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(
            {'message': "Qoldiq muvaffaqiyatli o'chirildi."},
            status=status.HTTP_200_OK,
        )


# ============================================================
# HARAKAT (KIRIM/CHIQIM/KO'CHIRISH) VIEWSET
# ============================================================

class StockMovementViewSet(viewsets.ModelViewSet):
    """
    Mahsulot harakatlarini boshqarish (kirim, chiqim, ko'chirish).

    Endpointlar:
      GET    /api/v1/warehouse/movements/       — ro'yxat
      POST   /api/v1/warehouse/movements/       — yangi harakat
      GET    /api/v1/warehouse/movements/{id}/  — tafsilotlar

    Muhim:
      Harakatlar o'zgartirilmaydi va o'chirilmaydi (immutable log).
      Xatolikni tuzatish uchun qarama-qarshi harakat yarating.

    Yaratishda:
      - IN:       to_branch/to_warehouse stock (+quantity)
      - OUT:      from_branch/from_warehouse stock (-quantity)
      - TRANSFER: from_* stock (-quantity), to_* stock (+quantity)
    """
    http_method_names = ['get', 'post']

    def get_permissions(self):
        return [IsAuthenticated(), CanAccess('ombor')]

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
            .select_related(
                'product',
                'from_branch', 'from_warehouse',
                'to_branch', 'to_warehouse',
                'worker__user',
            )
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        worker = getattr(self.request.user, 'worker', None)
        if worker:
            context['store'] = worker.store
        return context

    def _update_stock(self, product, branch, warehouse, delta):
        """
        Berilgan joydagi qoldiqni delta ga o'zgartiradi.
        delta > 0 — qo'shish, delta < 0 — ayirish.
        """
        filter_kwargs = {'product': product}
        if branch:
            filter_kwargs['branch'] = branch
        else:
            filter_kwargs['warehouse'] = warehouse

        stock, _ = Stock.objects.get_or_create(
            **filter_kwargs,
            defaults={'quantity': 0},
        )
        stock.quantity += delta
        stock.save(update_fields=['quantity', 'updated_on'])

    def perform_create(self, serializer):
        worker   = getattr(self.request.user, 'worker', None)
        instance = serializer.save(worker=worker)

        qty = instance.quantity

        if instance.movement_type == MovementType.IN:
            self._update_stock(
                instance.product,
                instance.to_branch,
                instance.to_warehouse,
                +qty,
            )
        elif instance.movement_type == MovementType.OUT:
            self._update_stock(
                instance.product,
                instance.from_branch,
                instance.from_warehouse,
                -qty,
            )
        elif instance.movement_type == MovementType.TRANSFER:
            self._update_stock(
                instance.product,
                instance.from_branch,
                instance.from_warehouse,
                -qty,
            )
            self._update_stock(
                instance.product,
                instance.to_branch,
                instance.to_warehouse,
                +qty,
            )

        from_loc = instance.from_branch or instance.from_warehouse
        to_loc   = instance.to_branch   or instance.to_warehouse
        from_name = from_loc.name if from_loc else '—'
        to_name   = to_loc.name   if to_loc   else '—'

        AuditLog.objects.create(
            actor=self.request.user,
            action=AuditLog.Action.CREATE,
            target_model='StockMovement',
            target_id=instance.id,
            description=(
                f"{instance.get_movement_type_display()}: "
                f"'{instance.product.name}' × {instance.quantity} "
                f"({from_name} → {to_name})"
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
