"""
============================================================
WAREHOUSE APP — View'lar
============================================================
ViewSet'lar:
  CategoryViewSet      — Kategoriyalarni boshqarish
  SubCategoryViewSet   — Subkategoriyalarni boshqarish (BOSQICH 1.1)
  CurrencyViewSet      — Valyutalarni boshqarish (BOSQICH 1.3)
  ExchangeRateViewSet  — Valyuta kurslarini boshqarish (BOSQICH 1.3)
  ProductViewSet       — Mahsulotlarni boshqarish + barcode_image action (BOSQICH 1.2)
  WarehouseViewSet     — Omborlarni boshqarish (BOSQICH 6)
  StockViewSet         — Ombor qoldiqlarini boshqarish (branch|warehouse)
  StockMovementViewSet — Kirim/chiqim harakatlarini boshqarish (branch|warehouse, FIFO)
  TransferViewSet      — Guruhlab ko'chirish (BOSQICH 1.6, FIFO propagatsiya)
  StockBatchViewSet    — FIFO partiyalar (read-only, BOSQICH 1.7)
  WastageRecordViewSet — Isrof yozuvlari (B7, POST → StockMovement(OUT) avtomatik)
  StockAuditViewSet    — Inventarizatsiya (B8, confirm → StockMovement(IN|OUT) avtomatik)

Ruxsatlar:
  list/retrieve → CanAccess('mahsulotlar') yoki CanAccess('ombor')
  create/update/destroy → IsManagerOrAbove

StockMovement:
  Harakatlar faqat POST (create) bilan yaratiladi.
  UPDATE va DELETE yo'q — harakatlar immutable.
  Yaratishda Stock qoldig'i avtomatik yangilanadi.
  IN harakatda unit_cost bo'lsa → StockBatch yaratiladi (FIFO).
  OUT harakatda FIFO dan narx hisoblanadi → unit_cost saqlashadi.
"""

from decimal import Decimal

from django.db import transaction
from django.db.models import F, Sum
from django.http import HttpResponse
from django.utils import timezone

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accaunt.models import AuditLog
from accaunt.permissions import CanAccess, IsManagerOrAbove

from config.cache_utils import get_store_settings

from .models import (
    AuditStatus,
    Category,
    Currency,
    ExchangeRate,
    MovementType,
    Product,
    Stock,
    StockAudit,
    StockAuditItem,
    StockBatch,
    StockMovement,
    SubCategory,
    Transfer,
    TransferStatus,
    Warehouse,
    WastageRecord,
)
from .serializers import (
    CategoryCreateSerializer,
    CategoryDetailSerializer,
    CategoryListSerializer,
    CategoryUpdateSerializer,
    CurrencyCreateSerializer,
    CurrencyDetailSerializer,
    CurrencyListSerializer,
    ExchangeRateCreateSerializer,
    ExchangeRateDetailSerializer,
    ExchangeRateListSerializer,
    MovementCreateSerializer,
    MovementDetailSerializer,
    MovementListSerializer,
    ProductCreateSerializer,
    ProductDetailSerializer,
    ProductListSerializer,
    ProductUpdateSerializer,
    StockAuditCreateSerializer,
    StockAuditDetailSerializer,
    StockAuditItemUpdateSerializer,
    StockAuditListSerializer,
    StockBatchSerializer,
    StockByProductSerializer,
    StockCreateSerializer,
    StockDetailSerializer,
    StockListSerializer,
    StockUpdateSerializer,
    SubCategoryCreateSerializer,
    SubCategoryDetailSerializer,
    SubCategoryListSerializer,
    SubCategoryUpdateSerializer,
    TransferCreateSerializer,
    TransferDetailSerializer,
    TransferListSerializer,
    WastageRecordCreateSerializer,
    WastageRecordDetailSerializer,
    WastageRecordListSerializer,
    WarehouseCreateSerializer,
    WarehouseDetailSerializer,
    WarehouseListSerializer,
    WarehouseUpdateSerializer,
)
from .utils import fifo_deduct, generate_batch_code


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
        return Category.objects.filter(store=worker.store)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        worker = getattr(self.request.user, 'worker', None)
        if worker:
            context['store'] = worker.store
        return context

    def perform_create(self, serializer):
        worker   = self.request.user.worker
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
        """Hard delete — kategoriyani bazadan o'chiradi."""
        AuditLog.objects.create(
            actor=self.request.user,
            action=AuditLog.Action.DELETE,
            target_model='Category',
            target_id=instance.id,
            description=f"Kategoriya o'chirildi: '{instance.name}'",
        )
        instance.delete()

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
        if not serializer.validated_data:
            return Response(
                {'message': "Yangilash uchun kamida bitta maydon yuborilishi kerak."},
                status=status.HTTP_400_BAD_REQUEST,
            )
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
# SUBKATEGORIYA VIEWSET (BOSQICH 1.1)
# ============================================================

class SubCategoryViewSet(viewsets.ModelViewSet):
    """
    Subkategoriyalarni boshqarish.

    Endpointlar:
      GET    /api/v1/warehouse/subcategories/          — ro'yxat
      POST   /api/v1/warehouse/subcategories/          — yaratish (manager+)
      GET    /api/v1/warehouse/subcategories/{id}/     — tafsilotlar
      PATCH  /api/v1/warehouse/subcategories/{id}/     — yangilash (manager+)
      DELETE /api/v1/warehouse/subcategories/{id}/     — o'chirish (manager+, hard delete)

    Filter:
      ?category=<id>   — Kategoriya bo'yicha filter

    Eslatma:
      StoreSettings.subcategory_enabled=True bo'lganda frontend ko'rsatadi.
      Endpoint har doim mavjud, frontend sozlama asosida yashiradi/ko'rsatadi.
    """
    http_method_names = ['get', 'post', 'patch', 'delete']

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated(), CanAccess('mahsulotlar')]
        return [IsAuthenticated(), IsManagerOrAbove()]

    def get_serializer_class(self):
        if self.action == 'list':
            return SubCategoryListSerializer
        if self.action == 'create':
            return SubCategoryCreateSerializer
        if self.action in ('update', 'partial_update'):
            return SubCategoryUpdateSerializer
        return SubCategoryDetailSerializer

    def get_queryset(self):
        worker = getattr(self.request.user, 'worker', None)
        if not worker or not worker.store:
            return SubCategory.objects.none()

        qs = SubCategory.objects.filter(
            store=worker.store
        ).select_related('category', 'store')

        # Kategoriya bo'yicha filter
        category_id = self.request.query_params.get('category')
        if category_id:
            qs = qs.filter(category_id=category_id)

        return qs

    def get_serializer_context(self):
        context = super().get_serializer_context()
        worker = getattr(self.request.user, 'worker', None)
        if worker:
            context['store'] = worker.store
        return context

    def perform_create(self, serializer):
        worker   = self.request.user.worker
        instance = serializer.save(store=worker.store)
        AuditLog.objects.create(
            actor=self.request.user,
            action=AuditLog.Action.CREATE,
            target_model='SubCategory',
            target_id=instance.id,
            description=f"Subkategoriya yaratildi: '{instance.category.name} → {instance.name}'",
        )

    def perform_update(self, serializer):
        instance = serializer.save()
        AuditLog.objects.create(
            actor=self.request.user,
            action=AuditLog.Action.UPDATE,
            target_model='SubCategory',
            target_id=instance.id,
            description=f"Subkategoriya yangilandi: '{instance.name}'",
        )

    def perform_destroy(self, instance: SubCategory):
        """Hard delete — subkategoriyani bazadan o'chiradi."""
        AuditLog.objects.create(
            actor=self.request.user,
            action=AuditLog.Action.DELETE,
            target_model='SubCategory',
            target_id=instance.id,
            description=f"Subkategoriya o'chirildi: '{instance.name}'",
        )
        instance.delete()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            {
                'message': "Subkategoriya muvaffaqiyatli yaratildi.",
                'data': SubCategoryDetailSerializer(
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
        if not serializer.validated_data:
            return Response(
                {'message': "Yangilash uchun kamida bitta maydon yuborilishi kerak."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        self.perform_update(serializer)
        return Response(
            {
                'message': "Subkategoriya muvaffaqiyatli yangilandi.",
                'data': SubCategoryDetailSerializer(
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
            {'message': "Subkategoriya muvaffaqiyatli o'chirildi."},
            status=status.HTTP_200_OK,
        )


# ============================================================
# VALYUTA VIEWSET (BOSQICH 1.3)
# ============================================================

class CurrencyViewSet(viewsets.ModelViewSet):
    """
    Valyutalarni boshqarish.

    Endpointlar:
      GET    /api/v1/warehouse/currencies/       — ro'yxat (barcha foydalanuvchilar)
      POST   /api/v1/warehouse/currencies/       — yaratish (manager+)
      GET    /api/v1/warehouse/currencies/{id}/  — tafsilotlar
      PATCH  /api/v1/warehouse/currencies/{id}/  — yangilash (manager+)
      DELETE /api/v1/warehouse/currencies/{id}/  — o'chirish (manager+)

    Eslatma:
      Valyutalar global (store bilan bog'liq emas).
      Migration da dastlabki valyutalar seed qilinadi: UZS, USD, EUR, RUB, CNY.
    """
    http_method_names = ['get', 'post', 'patch', 'delete']

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsManagerOrAbove()]

    def get_serializer_class(self):
        if self.action == 'list':
            return CurrencyListSerializer
        if self.action == 'create':
            return CurrencyCreateSerializer
        return CurrencyDetailSerializer

    def get_queryset(self):
        return Currency.objects.all().order_by('code')

    def perform_create(self, serializer):
        instance = serializer.save()
        AuditLog.objects.create(
            actor=self.request.user,
            action=AuditLog.Action.CREATE,
            target_model='Currency',
            target_id=instance.id,
            description=f"Valyuta qo'shildi: '{instance.code} ({instance.name})'",
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            {
                'message': "Valyuta muvaffaqiyatli qo'shildi.",
                'data': CurrencyDetailSerializer(serializer.instance).data,
            },
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        # PATCH uchun faqat name, symbol o'zgartiriladi (code va is_base himoyalangan)
        allowed_fields = {'name', 'symbol'}
        data = {k: v for k, v in request.data.items() if k in allowed_fields}
        if not data:
            return Response(
                {'message': "Yangilash uchun kamida bitta maydon yuborilishi kerak."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = self.get_serializer(instance, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(
            {
                'message': "Valyuta muvaffaqiyatli yangilandi.",
                'data': CurrencyDetailSerializer(instance).data,
            },
            status=status.HTTP_200_OK,
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.is_base:
            return Response(
                {'error': "Asosiy valyutani o'chirish mumkin emas."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        instance.delete()
        return Response(
            {'message': "Valyuta muvaffaqiyatli o'chirildi."},
            status=status.HTTP_200_OK,
        )


# ============================================================
# VALYUTA KURSI VIEWSET (BOSQICH 1.3)
# ============================================================

class ExchangeRateViewSet(viewsets.ModelViewSet):
    """
    Valyuta kurslarini boshqarish.

    Endpointlar:
      GET    /api/v1/warehouse/exchange-rates/       — ro'yxat (so'nggi kurslar)
      POST   /api/v1/warehouse/exchange-rates/       — qo'lda kiritish (manager+)
      GET    /api/v1/warehouse/exchange-rates/{id}/  — tafsilotlar

    Filter:
      ?currency=USD      — valyuta kodi bo'yicha
      ?date=2026-03-03   — sana bo'yicha

    Eslatma:
      Kurslar CBU API dan har kuni 09:00 da Celery task orqali avtomatik yangilanadi.
      Bu endpoint faqat ko'rish va qo'lda kiritish uchun.
    """
    http_method_names = ['get', 'post']

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsManagerOrAbove()]

    def get_serializer_class(self):
        if self.action == 'list':
            return ExchangeRateListSerializer
        if self.action == 'create':
            return ExchangeRateCreateSerializer
        return ExchangeRateDetailSerializer

    def get_queryset(self):
        qs = ExchangeRate.objects.select_related('currency').order_by('-date', 'currency__code')

        # Valyuta kodi bo'yicha filter
        currency_code = self.request.query_params.get('currency')
        if currency_code:
            qs = qs.filter(currency__code=currency_code.upper())

        # Sana bo'yicha filter
        date_str = self.request.query_params.get('date')
        if date_str:
            qs = qs.filter(date=date_str)

        return qs

    def perform_create(self, serializer):
        instance = serializer.save()
        AuditLog.objects.create(
            actor=self.request.user,
            action=AuditLog.Action.CREATE,
            target_model='ExchangeRate',
            target_id=instance.id,
            description=(
                f"Valyuta kursi kiritildi: {instance.currency.code} = "
                f"{instance.rate} UZS ({instance.date})"
            ),
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            {
                'message': "Valyuta kursi muvaffaqiyatli kiritildi.",
                'data': ExchangeRateDetailSerializer(serializer.instance).data,
            },
            status=status.HTTP_201_CREATED,
        )


# ============================================================
# MAHSULOT VIEWSET (BOSQICH 1.2 — barcode action qo'shildi)
# ============================================================

class ProductViewSet(viewsets.ModelViewSet):
    """
    Mahsulotlarni boshqarish.

    Endpointlar:
      GET    /api/v1/warehouse/products/                — ro'yxat
      POST   /api/v1/warehouse/products/                — yaratish (manager+)
      GET    /api/v1/warehouse/products/{id}/           — tafsilotlar
      PATCH  /api/v1/warehouse/products/{id}/           — yangilash (manager+)
      DELETE /api/v1/warehouse/products/{id}/           — o'chirish (manager+, hard delete)
      GET    /api/v1/warehouse/products/{id}/barcode/   — barcode PNG rasm (BOSQICH 1.2)

    Barcode (BOSQICH 1.2):
      - Yaratishda barcode yuborilmasa → EAN-13 AUTO-GENERATE (prefix 2XXXXX)
      - /barcode/ endpoint → PNG rasm qaytaradi
      - Format: 20 + store_id(5) + seq(5) + check(1) = 13 ta raqam

    Filter/Search:
      ?search=mahsulot_nomi
      ?category=<id>
      ?subcategory=<id>
      ?status=active
    """
    http_method_names = ['get', 'post', 'patch', 'delete']

    def get_permissions(self):
        if self.action in ('list', 'retrieve', 'barcode_image'):
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

        qs = (
            Product.objects
            .filter(store=worker.store)
            .select_related('category', 'subcategory', 'store', 'price_currency')
        )

        # Filter: kategoriya
        category_id = self.request.query_params.get('category')
        if category_id:
            qs = qs.filter(category_id=category_id)

        # Filter: subkategoriya
        subcategory_id = self.request.query_params.get('subcategory')
        if subcategory_id:
            qs = qs.filter(subcategory_id=subcategory_id)

        # Filter: status
        status_val = self.request.query_params.get('status')
        if status_val:
            qs = qs.filter(status=status_val)

        return qs

    def get_serializer_context(self):
        context = super().get_serializer_context()
        worker = getattr(self.request.user, 'worker', None)
        if worker:
            context['store'] = worker.store
        return context

    def perform_create(self, serializer):
        """
        Mahsulot yaratish.
        Barcode yo'q bo'lsa → EAN-13 avtomatik generatsiya qilinadi.
        """
        worker = self.request.user.worker

        # Barcode auto-generate (BOSQICH 1.2)
        barcode_val = serializer.validated_data.get('barcode')
        if not barcode_val:
            from .utils import generate_unique_barcode
            barcode_val = generate_unique_barcode(worker.store.id)

        instance = serializer.save(store=worker.store, barcode=barcode_val)
        AuditLog.objects.create(
            actor=self.request.user,
            action=AuditLog.Action.CREATE,
            target_model='Product',
            target_id=instance.id,
            description=f"Mahsulot yaratildi: '{instance.name}' (barcode: {instance.barcode})",
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
        """Hard delete — mahsulotni bazadan o'chiradi."""
        AuditLog.objects.create(
            actor=self.request.user,
            action=AuditLog.Action.DELETE,
            target_model='Product',
            target_id=instance.id,
            description=f"Mahsulot o'chirildi: '{instance.name}'",
        )
        instance.delete()

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
        if not serializer.validated_data:
            return Response(
                {'message': "Yangilash uchun kamida bitta maydon yuborilishi kerak."},
                status=status.HTTP_400_BAD_REQUEST,
            )
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

    # ── BARCODE IMAGE ACTION (BOSQICH 1.2) ──────────────────
    @action(detail=True, methods=['get'], url_path='barcode')
    def barcode_image(self, request, pk=None):
        """
        Mahsulotning EAN-13 barcode rasmini qaytaradi.

        GET /api/v1/warehouse/products/{id}/barcode/
        GET /api/v1/warehouse/products/{id}/barcode/?format=svg

        Parametrlar:
          ?format=png  — PNG rasm (standart, Pillow kerak)
          ?format=svg  — SVG vektor (Pillow shart emas)

        Javob:
          Content-Type: image/png  yoki  image/svg+xml
        """
        product = self.get_object()

        if not product.barcode:
            return Response(
                {'error': "Bu mahsulotda shtrix-kod yo'q."},
                status=status.HTTP_404_NOT_FOUND,
            )

        fmt = request.query_params.get('format', 'png').lower()

        try:
            from .utils import get_barcode_image, get_barcode_svg

            if fmt == 'svg':
                content      = get_barcode_svg(product.barcode)
                content_type = 'image/svg+xml'
            else:
                content      = get_barcode_image(product.barcode)
                content_type = 'image/png'

            response = HttpResponse(content, content_type=content_type)
            response['Content-Disposition'] = (
                f'inline; filename="barcode_{product.barcode}.{fmt}"'
            )
            return response

        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


# ============================================================
# OMBOR (WAREHOUSE) VIEWSET
# ============================================================

class WarehouseViewSet(viewsets.ModelViewSet):
    """
    Omborlarni boshqarish.

    Endpointlar:
      GET    /api/v1/warehouse/warehouses/       — ro'yxat
      POST   /api/v1/warehouse/warehouses/       — yangi ombor qo'shish (manager+)
      GET    /api/v1/warehouse/warehouses/{id}/  — tafsilotlar
      PATCH  /api/v1/warehouse/warehouses/{id}/  — yangilash (manager+)
      DELETE /api/v1/warehouse/warehouses/{id}/  — o'chirish (manager+, hard delete)

    Multi-tenant: har bir ombor bitta do'konga tegishli.
    Soft delete: is_active=False bilan o'chiriladi (haqiqiy o'chirish yo'q).
    """
    http_method_names = ['get', 'post', 'patch', 'delete']

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated(), CanAccess('ombor')]
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
        return Warehouse.objects.filter(store=worker.store)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        worker = getattr(self.request.user, 'worker', None)
        if worker:
            context['store'] = worker.store
        return context

    def perform_create(self, serializer):
        worker = getattr(self.request.user, 'worker', None)
        instance = serializer.save(store=worker.store)
        AuditLog.objects.create(
            actor=self.request.user,
            action=AuditLog.Action.CREATE,
            target_model='Warehouse',
            target_id=instance.id,
            description=f"Yangi ombor qo'shildi: '{instance.name}'",
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
        """Hard delete — omborni bazadan o'chiradi."""
        AuditLog.objects.create(
            actor=self.request.user,
            action=AuditLog.Action.DELETE,
            target_model='Warehouse',
            target_id=instance.id,
            description=f"Ombor o'chirildi: '{instance.name}'",
        )
        instance.delete()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            {
                'message': "Ombor muvaffaqiyatli qo'shildi.",
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
        if not serializer.validated_data:
            return Response(
                {'message': "Yangilash uchun kamida bitta maydon yuborilishi kerak."},
                status=status.HTTP_400_BAD_REQUEST,
            )
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
            return [IsAuthenticated(), CanAccess('ombor')]
        return [IsAuthenticated(), IsManagerOrAbove()]

    def get_serializer_class(self):
        if self.action == 'list':
            return StockListSerializer
        if self.action == 'by_product':
            return StockByProductSerializer
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

    def _location_name(self, instance: Stock) -> str:
        if instance.branch_id:
            return instance.branch.name
        return instance.warehouse.name if instance.warehouse_id else '—'

    def perform_create(self, serializer):
        instance = serializer.save()
        AuditLog.objects.create(
            actor=self.request.user,
            action=AuditLog.Action.CREATE,
            target_model='Stock',
            target_id=instance.id,
            description=(
                f"Ombor qoldig'i qo'shildi: '{instance.product.name}' "
                f"({self._location_name(instance)}) = {instance.quantity}"
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
                f"({self._location_name(instance)}) = {instance.quantity}"
            ),
        )

    def perform_destroy(self, instance: Stock):
        pk   = instance.id
        name = f"{instance.product.name} ({self._location_name(instance)})"
        AuditLog.objects.create(
            actor=self.request.user,
            action=AuditLog.Action.DELETE,
            target_model='Stock',
            target_id=pk,
            description=f"Ombor qoldig'i o'chirildi: '{name}'",
        )
        instance.delete()

    @action(detail=False, methods=['get'], url_path='by-product')
    def by_product(self, request):
        """
        Mahsulot bo'yicha guruhlangan qoldiqlar.

        GET /api/v1/warehouse/stocks/by-product/

        Har bir mahsulot — bitta obyekt.
        Joylashuvlar (filial/ombor) 'locations' ichida nested ko'rinishda.
        """
        from itertools import groupby
        from operator import attrgetter

        qs = (
            self.get_queryset()
            .order_by('product__name', 'product_id')
        )

        result = []
        for _product_id, stock_group in groupby(qs, key=attrgetter('product_id')):
            stocks = list(stock_group)
            first  = stocks[0]
            total  = sum(s.quantity for s in stocks)

            locations = [
                {
                    'stock_id'     : s.id,
                    'location_type': 'branch' if s.branch_id else 'warehouse',
                    'location_id'  : s.branch_id or s.warehouse_id,
                    'location_name': (
                        s.branch.name if s.branch_id
                        else (s.warehouse.name if s.warehouse_id else None)
                    ),
                    'quantity'  : str(s.quantity),
                    'updated_on': (
                        s.updated_on.strftime('%Y-%m-%d | %H:%M')
                        if s.updated_on else None
                    ),
                }
                for s in stocks
            ]

            result.append({
                'product_id'    : first.product.id,
                'product_name'  : first.product.name,
                'product_unit'  : first.product.get_unit_display(),
                'total_quantity': str(total),
                'locations'     : locations,
            })

        return Response(result)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            {
                'message': "Ombor qoldig'i muvaffaqiyatli qo'shildi.",
                'data': StockDetailSerializer(
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
        if not serializer.validated_data:
            return Response(
                {'message': "Yangilash uchun kamida bitta maydon yuborilishi kerak."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        self.perform_update(serializer)
        return Response(
            {
                'message': "Ombor qoldig'i muvaffaqiyatli yangilandi.",
                'data': StockDetailSerializer(
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
      - Race condition yo'q: @transaction.atomic + select_for_update() + F()
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
            .select_related('product', 'branch', 'warehouse', 'worker__user')
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        worker = getattr(self.request.user, 'worker', None)
        if worker:
            context['store'] = worker.store
        return context

    def _location_name(self, instance: StockMovement) -> str:
        if instance.branch_id:
            return instance.branch.name
        return instance.warehouse.name if instance.warehouse_id else '—'

    @transaction.atomic
    def perform_create(self, serializer):
        worker    = getattr(self.request.user, 'worker', None)
        store     = getattr(worker, 'store', None)
        unit_cost = serializer.validated_data.get('unit_cost')
        instance  = serializer.save(worker=worker)

        # Stock qoldig'ini yangilash (branch YOKI warehouse)
        # get_or_create + F() expression — parallel so'rovlarda race condition yo'q
        if instance.branch_id:
            stock, _ = Stock.objects.select_for_update().get_or_create(
                product=instance.product,
                branch=instance.branch,
                warehouse=None,
                defaults={'quantity': 0},
            )
        else:
            stock, _ = Stock.objects.select_for_update().get_or_create(
                product=instance.product,
                branch=None,
                warehouse=instance.warehouse,
                defaults={'quantity': 0},
            )

        if instance.movement_type == MovementType.IN:
            Stock.objects.filter(pk=stock.pk).update(
                quantity=F('quantity') + instance.quantity,
                updated_on=timezone.now(),
            )
            # ── FIFO: IN harakat uchun yangi partiya yaratish ──
            if unit_cost is not None and store:
                batch_code = generate_batch_code(store)
                StockBatch.objects.create(
                    batch_code   = batch_code,
                    product      = instance.product,
                    branch       = instance.branch,
                    warehouse    = instance.warehouse,
                    unit_cost    = unit_cost,
                    qty_received = instance.quantity,
                    qty_left     = instance.quantity,
                    movement     = instance,
                    store        = store,
                )
                # ── AVCO: purchase_price o'rtacha tannarx bilan yangilash ──
                # Barcha aktiv partiyalar bo'yicha weighted average hisoblanadi
                result = (
                    StockBatch.objects
                    .filter(product=instance.product, qty_left__gt=0)
                    .aggregate(
                        total_value=Sum(F('unit_cost') * F('qty_left')),
                        total_qty=Sum('qty_left'),
                    )
                )
                if result['total_qty']:
                    avg = result['total_value'] / result['total_qty']
                    Product.objects.filter(pk=instance.product_id).update(purchase_price=avg)
        else:
            Stock.objects.filter(pk=stock.pk).update(
                quantity=F('quantity') - instance.quantity,
                updated_on=timezone.now(),
            )
            # ── FIFO: OUT harakat uchun partiyalardan yechib olish ──
            if store:
                loc_kwargs = {
                    'branch':    instance.branch,
                    'warehouse': instance.warehouse,
                }
                deductions, total_cost = fifo_deduct(
                    instance.product, loc_kwargs, instance.quantity
                )
                if instance.quantity > 0:
                    avg_cost = total_cost / instance.quantity
                    StockMovement.objects.filter(pk=instance.pk).update(
                        unit_cost=avg_cost
                    )

        AuditLog.objects.create(
            actor=self.request.user,
            action=AuditLog.Action.CREATE,
            target_model='StockMovement',
            target_id=instance.id,
            description=(
                f"{instance.get_movement_type_display()}: "
                f"'{instance.product.name}' × {instance.quantity} "
                f"({self._location_name(instance)})"
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


# ============================================================
# TRANSFER VIEWSET
# ============================================================

class TransferViewSet(viewsets.ModelViewSet):
    """
    Tovar ko'chirish (Transfer) — bir nechta mahsulotni guruhlab jo'natish.

    Endpointlar:
      GET    /api/v1/warehouse/transfers/              — ro'yxat
      POST   /api/v1/warehouse/transfers/              — yangi transfer (pending)
      GET    /api/v1/warehouse/transfers/{id}/         — tafsilotlar
      POST   /api/v1/warehouse/transfers/{id}/confirm/ — tasdiqlash (stock yangilanadi)
      POST   /api/v1/warehouse/transfers/{id}/cancel/  — bekor qilish (faqat pending)

    Muhim:
      Yaratishda status=pending — stock o'zgarmaydi.
      confirm() da BARCHA mahsulotlar atomik yangilanadi (transaction.atomic).
      Agar bitta mahsulotda qoldiq yetishmasa → HECH BIRI o'zgarmaydi.
      confirmed va cancelled — immutable (o'zgartirib bo'lmaydi).
    """
    http_method_names = ['get', 'post']

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated(), CanAccess('ombor')]
        return [IsAuthenticated(), IsManagerOrAbove()]

    def get_serializer_class(self):
        if self.action == 'list':
            return TransferListSerializer
        if self.action == 'create':
            return TransferCreateSerializer
        return TransferDetailSerializer

    def get_queryset(self):
        worker = getattr(self.request.user, 'worker', None)
        if not worker or not worker.store:
            return Transfer.objects.none()
        return (
            Transfer.objects
            .filter(store=worker.store)
            .select_related(
                'from_branch', 'from_warehouse',
                'to_branch',   'to_warehouse',
                'worker__user',
            )
            .prefetch_related('items__product')
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        worker = getattr(self.request.user, 'worker', None)
        if worker:
            context['store']  = worker.store
            context['worker'] = worker
        return context

    def _from_name(self, transfer: Transfer) -> str:
        if transfer.from_branch_id:
            return transfer.from_branch.name
        return transfer.from_warehouse.name if transfer.from_warehouse_id else '—'

    def _to_name(self, transfer: Transfer) -> str:
        if transfer.to_branch_id:
            return transfer.to_branch.name
        return transfer.to_warehouse.name if transfer.to_warehouse_id else '—'

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        transfer = serializer.save()
        AuditLog.objects.create(
            actor=request.user,
            action=AuditLog.Action.CREATE,
            target_model='Transfer',
            target_id=transfer.id,
            description=(
                f"Transfer yaratildi (pending): "
                f"{self._from_name(transfer)} → {self._to_name(transfer)}, "
                f"{transfer.items.count()} ta mahsulot"
            ),
        )
        return Response(
            {
                'message': "Transfer muvaffaqiyatli yaratildi. Tasdiqlash uchun /confirm/ ga murojaat qiling.",
                'data': TransferDetailSerializer(
                    transfer,
                    context=self.get_serializer_context(),
                ).data,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['post'], url_path='confirm')
    @transaction.atomic
    def confirm(self, request, pk=None):
        """
        Transferni tasdiqlash — barcha mahsulotlar atomik yangilanadi.

        Jarayon:
          1. Status pending ekanligini tekshirish
          2. Barcha itemlar uchun manbaa stockni LOCK (select_for_update)
          3. Qoldiq yetarliligini tekshirish (HAMMASI tekshiriladi, keyin yangilash)
          4. Har bir item uchun:
             a. StockMovement(OUT) — manbaa
             b. Manbaa Stock kamayadi (F())
             c. StockMovement(IN)  — manzil
             d. Manzil Stock ko'payadi (get_or_create + F())
          5. Transfer.status = confirmed, confirmed_at = now()
          6. AuditLog
        """
        transfer = self.get_object()

        if transfer.status != TransferStatus.PENDING:
            return Response(
                {'error': f"Faqat 'pending' transferni tasdiqlash mumkin. Hozirgi holat: '{transfer.get_status_display()}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        items = list(transfer.items.select_related('product').all())
        if not items:
            return Response(
                {'error': "Transfer bo'sh — hech qanday mahsulot yo'q."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Manbaa joyi
        from_branch    = transfer.from_branch
        from_warehouse = transfer.from_warehouse

        # Manzil joyi
        to_branch    = transfer.to_branch
        to_warehouse = transfer.to_warehouse

        # ── QADAM 1: Barcha manbaa stocklarni LOCK va tekshirish ──────
        errors = []
        locked_stocks = {}

        for item in items:
            if from_branch:
                stock, _ = Stock.objects.select_for_update().get_or_create(
                    product=item.product,
                    branch=from_branch,
                    warehouse=None,
                    defaults={'quantity': 0},
                )
            else:
                stock, _ = Stock.objects.select_for_update().get_or_create(
                    product=item.product,
                    branch=None,
                    warehouse=from_warehouse,
                    defaults={'quantity': 0},
                )
            locked_stocks[item.product_id] = stock

            if stock.quantity < item.quantity:
                errors.append(
                    f"'{item.product.name}': mavjud {stock.quantity}, "
                    f"kerakli {item.quantity}."
                )

        if errors:
            # Hech narsa o'zgarmaydi — transaction rollback
            raise ValidationError({
                'detail': "Qoldiq yetarli emas — transfer bekor qilindi.",
                'errors': errors,
            })

        # ── QADAM 2: Har bir item uchun OUT + IN ──────────────────────
        worker = getattr(request.user, 'worker', None)
        store  = transfer.store

        for item in items:
            from_stock = locked_stocks[item.product_id]

            # ── FIFO: manbaa partiyalardan yechib olish ──────────────
            loc_from = {
                'branch':    from_branch,
                'warehouse': from_warehouse,
            }
            deductions, total_cost = fifo_deduct(
                item.product, loc_from, item.quantity
            )
            avg_cost = (
                total_cost / item.quantity
                if item.quantity > 0
                else Decimal('0')
            )

            # OUT — manbaa
            out_movement = StockMovement.objects.create(
                product       = item.product,
                branch        = from_branch,
                warehouse     = from_warehouse,
                movement_type = MovementType.OUT,
                quantity      = item.quantity,
                unit_cost     = avg_cost,
                worker        = worker,
                note          = f"Transfer #{transfer.id} chiqim",
            )
            Stock.objects.filter(pk=from_stock.pk).update(
                quantity   = F('quantity') - item.quantity,
                updated_on = timezone.now(),
            )

            # IN — manzil
            in_movement = StockMovement.objects.create(
                product       = item.product,
                branch        = to_branch,
                warehouse     = to_warehouse,
                movement_type = MovementType.IN,
                quantity      = item.quantity,
                unit_cost     = avg_cost,
                worker        = worker,
                note          = f"Transfer #{transfer.id} kirim",
            )
            if to_branch:
                to_stock, _ = Stock.objects.select_for_update().get_or_create(
                    product=item.product,
                    branch=to_branch,
                    warehouse=None,
                    defaults={'quantity': 0},
                )
            else:
                to_stock, _ = Stock.objects.select_for_update().get_or_create(
                    product=item.product,
                    branch=None,
                    warehouse=to_warehouse,
                    defaults={'quantity': 0},
                )
            Stock.objects.filter(pk=to_stock.pk).update(
                quantity   = F('quantity') + item.quantity,
                updated_on = timezone.now(),
            )

            # ── FIFO: manzilda yangi batch yaratish ─────────────────
            batch_code = generate_batch_code(store)
            StockBatch.objects.create(
                batch_code   = batch_code,
                product      = item.product,
                branch       = to_branch,
                warehouse    = to_warehouse,
                unit_cost    = avg_cost,
                qty_received = item.quantity,
                qty_left     = item.quantity,
                movement     = in_movement,
                store        = store,
            )

        # ── QADAM 3: Transfer tasdiqlash ──────────────────────────────
        transfer.status       = TransferStatus.CONFIRMED
        transfer.confirmed_at = timezone.now()
        transfer.save(update_fields=['status', 'confirmed_at'])

        total_qty = sum(item.quantity for item in items)
        AuditLog.objects.create(
            actor=request.user,
            action=AuditLog.Action.UPDATE,
            target_model='Transfer',
            target_id=transfer.id,
            description=(
                f"Transfer tasdiqlandi: "
                f"{self._from_name(transfer)} → {self._to_name(transfer)}, "
                f"{len(items)} ta mahsulot, jami {total_qty} birlik"
            ),
        )

        return Response(
            {
                'message': "Transfer muvaffaqiyatli tasdiqlandi. Qoldiqlar yangilandi.",
                'data': TransferDetailSerializer(
                    transfer,
                    context=self.get_serializer_context(),
                ).data,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=['post'], url_path='cancel')
    def cancel(self, request, pk=None):
        """
        Transferni bekor qilish — faqat pending holatda.
        Stock o'zgarmaydi.
        """
        transfer = self.get_object()

        if transfer.status != TransferStatus.PENDING:
            return Response(
                {'error': f"Faqat 'pending' transferni bekor qilish mumkin. Hozirgi holat: '{transfer.get_status_display()}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        transfer.status = TransferStatus.CANCELLED
        transfer.save(update_fields=['status'])

        AuditLog.objects.create(
            actor=request.user,
            action=AuditLog.Action.DELETE,
            target_model='Transfer',
            target_id=transfer.id,
            description=(
                f"Transfer bekor qilindi: "
                f"{self._from_name(transfer)} → {self._to_name(transfer)}"
            ),
        )

        return Response(
            {
                'message': "Transfer bekor qilindi.",
                'data': TransferDetailSerializer(
                    transfer,
                    context=self.get_serializer_context(),
                ).data,
            },
            status=status.HTTP_200_OK,
        )


# ============================================================
# STOCKBATCH VIEWSET (FIFO PARTIYALAR)
# ============================================================

class StockBatchViewSet(viewsets.ReadOnlyModelViewSet):
    """
    FIFO partiyalarini ko'rish (faqat o'qish).

    Endpointlar:
      GET /api/v1/warehouse/batches/           — ro'yxat (?product=<id>)
      GET /api/v1/warehouse/batches/{id}/      — tafsilotlar

    Filtrlash:
      ?product=<id>  — ma'lum mahsulotning barcha partiyadlari

    Foydalanish:
      Mahsulotning FIFO tannarxini kuzatish, moliyaviy hisobot uchun.
      qty_left=0 bo'lgan partiyalar tamom (eski arxiv).
    """
    serializer_class = StockBatchSerializer

    def get_permissions(self):
        return [IsAuthenticated(), CanAccess('ombor')]

    def get_queryset(self):
        worker = getattr(self.request.user, 'worker', None)
        if not worker or not worker.store:
            return StockBatch.objects.none()
        qs = (
            StockBatch.objects
            .filter(store=worker.store)
            .select_related('product', 'branch', 'warehouse', 'movement')
        )
        product_id = self.request.query_params.get('product')
        if product_id:
            qs = qs.filter(product_id=product_id)
        return qs


# ============================================================
# ISROF (WASTAGE) VIEWSET  B7
# ============================================================

class WastageRecordViewSet(viewsets.ModelViewSet):
    """
    Isrof yozuvlarini boshqarish.

    Endpointlar:
      GET    /api/v1/warehouse/wastages/        — ro'yxat
      POST   /api/v1/warehouse/wastages/        — yangi isrof yozuvi
      GET    /api/v1/warehouse/wastages/{id}/   — tafsilotlar

    Muhim:
      Yaratilganda AVTOMATIK StockMovement(OUT) va Stock kamayadi (FIFO).
      Isrof yozuvlari o'zgartirilmaydi va o'chirilmaydi (immutable log).

    Filtrlash:
      ?branch=<id>     — filial bo'yicha
      ?warehouse=<id>  — ombor bo'yicha
      ?product=<id>    — mahsulot bo'yicha
      ?date=YYYY-MM-DD — sana bo'yicha

    Ruxsatlar:
      list/retrieve → CanAccess('ombor')
      create        → IsManagerOrAbove
    """
    http_method_names = ['get', 'post']

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated(), CanAccess('ombor')]
        return [IsAuthenticated(), IsManagerOrAbove()]

    def get_serializer_class(self):
        if self.action == 'list':
            return WastageRecordListSerializer
        if self.action == 'create':
            return WastageRecordCreateSerializer
        return WastageRecordDetailSerializer

    def get_queryset(self):
        worker = getattr(self.request.user, 'worker', None)
        if not worker or not worker.store:
            return WastageRecord.objects.none()
        qs = (
            WastageRecord.objects
            .filter(store=worker.store)
            .select_related('product', 'branch', 'warehouse', 'worker__user')
        )
        branch_id    = self.request.query_params.get('branch')
        warehouse_id = self.request.query_params.get('warehouse')
        product_id   = self.request.query_params.get('product')
        date_str     = self.request.query_params.get('date')
        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        if warehouse_id:
            qs = qs.filter(warehouse_id=warehouse_id)
        if product_id:
            qs = qs.filter(product_id=product_id)
        if date_str:
            qs = qs.filter(date=date_str)
        return qs

    def get_serializer_context(self):
        context = super().get_serializer_context()
        worker = getattr(self.request.user, 'worker', None)
        if worker:
            context['store'] = worker.store
        return context

    @transaction.atomic
    def perform_create(self, serializer):
        worker   = getattr(self.request.user, 'worker', None)
        store    = getattr(worker, 'store', None)
        settings = get_store_settings(store.id) if store else None

        # StoreSettings: isrof yoqilganligini tekshirish
        if settings and not settings.wastage_enabled:
            raise ValidationError({
                'detail': "Isrof funksiyasi bu do'konda o'chirib qo'yilgan."
            })

        instance = serializer.save(store=store, worker=worker)

        # ── Stock: FIFO yechish (select_for_update + F()) ──────────────────
        if instance.branch_id:
            stock, _ = Stock.objects.select_for_update().get_or_create(
                product=instance.product,
                branch=instance.branch,
                warehouse=None,
                defaults={'quantity': 0},
            )
        else:
            stock, _ = Stock.objects.select_for_update().get_or_create(
                product=instance.product,
                branch=None,
                warehouse=instance.warehouse,
                defaults={'quantity': 0},
            )

        Stock.objects.filter(pk=stock.pk).update(
            quantity=F('quantity') - instance.quantity,
            updated_on=timezone.now(),
        )

        # ── StockMovement(OUT) — immutable log ─────────────────────────────
        movement = StockMovement.objects.create(
            product       = instance.product,
            branch        = instance.branch,
            warehouse     = instance.warehouse,
            movement_type = MovementType.OUT,
            quantity      = instance.quantity,
            note          = f"Isrof: {instance.get_reason_display()}. {instance.note}".strip('. '),
            worker        = worker,
        )

        # ── FIFO: OUT harakati uchun partiyalardan yechib olish ────────────
        if store:
            loc_kwargs = {
                'branch':    instance.branch,
                'warehouse': instance.warehouse,
            }
            deductions, total_cost = fifo_deduct(
                instance.product, loc_kwargs, instance.quantity
            )
            if instance.quantity > 0 and deductions:
                avg_cost = total_cost / instance.quantity
                StockMovement.objects.filter(pk=movement.pk).update(unit_cost=avg_cost)

        AuditLog.objects.create(
            actor=self.request.user,
            action=AuditLog.Action.CREATE,
            target_model='WastageRecord',
            target_id=instance.id,
            description=(
                f"Isrof yozildi: '{instance.product.name}' × {instance.quantity} "
                f"({instance.get_reason_display()})"
            ),
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            {
                'message': "Isrof muvaffaqiyatli qayd etildi.",
                'data': WastageRecordDetailSerializer(
                    serializer.instance,
                    context=self.get_serializer_context(),
                ).data,
            },
            status=status.HTTP_201_CREATED,
        )


# ============================================================
# INVENTARIZATSIYA (STOCK AUDIT) VIEWSET  B8
# ============================================================

class StockAuditViewSet(viewsets.ModelViewSet):
    """
    Inventarizatsiyani boshqarish.

    Endpointlar:
      GET    /api/v1/warehouse/audits/                        — ro'yxat
      POST   /api/v1/warehouse/audits/                        — yangi inventarizatsiya (draft)
      GET    /api/v1/warehouse/audits/{id}/                   — tafsilotlar (nested items bilan)
      POST   /api/v1/warehouse/audits/{id}/confirm/           — tasdiqlash (StockMovement avtomatik)
      POST   /api/v1/warehouse/audits/{id}/cancel/            — bekor qilish (faqat draft)
      PATCH  /api/v1/warehouse/audits/{id}/items/{item_id}/   — satr actual_qty yangilash

    Holat o'tishi:
      draft → confirmed: har bir satr uchun diff asosida StockMovement(IN|OUT) yaratiladi.
      draft → cancelled: hech narsa o'zgarmaydi.

    Ruxsatlar:
      list/retrieve/update_item → CanAccess('ombor')
      create/confirm/cancel     → IsManagerOrAbove

    Filtrlash:
      ?status=draft|confirmed|cancelled
      ?branch=<id>
      ?warehouse=<id>
    """
    http_method_names = ['get', 'post', 'patch']

    def get_permissions(self):
        if self.action in ('list', 'retrieve', 'update_item'):
            return [IsAuthenticated(), CanAccess('ombor')]
        return [IsAuthenticated(), IsManagerOrAbove()]

    def get_serializer_class(self):
        if self.action == 'list':
            return StockAuditListSerializer
        if self.action == 'create':
            return StockAuditCreateSerializer
        return StockAuditDetailSerializer

    def get_queryset(self):
        worker = getattr(self.request.user, 'worker', None)
        if not worker or not worker.store:
            return StockAudit.objects.none()
        qs = (
            StockAudit.objects
            .filter(store=worker.store)
            .select_related('branch', 'warehouse', 'worker__user')
            .prefetch_related('items__product')
        )
        status_filter = self.request.query_params.get('status')
        branch_id     = self.request.query_params.get('branch')
        warehouse_id  = self.request.query_params.get('warehouse')
        if status_filter:
            qs = qs.filter(status=status_filter)
        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        if warehouse_id:
            qs = qs.filter(warehouse_id=warehouse_id)
        return qs

    def get_serializer_context(self):
        context = super().get_serializer_context()
        worker = getattr(self.request.user, 'worker', None)
        if worker:
            context['store'] = worker.store
        return context

    @transaction.atomic
    def perform_create(self, serializer):
        worker   = getattr(self.request.user, 'worker', None)
        store    = getattr(worker, 'store', None)
        settings = get_store_settings(store.id) if store else None

        # StoreSettings: inventarizatsiya yoqilganligini tekshirish
        if settings and not settings.stock_audit_enabled:
            raise ValidationError({
                'detail': "Inventarizatsiya funksiyasi bu do'konda o'chirib qo'yilgan."
            })

        audit = serializer.save(store=store, worker=worker)

        # ── StockAuditItem'larni avtomatik yaratish ────────────────────────
        # Tanlangan joy (branch|warehouse) dagi barcha Stock qatorlari uchun
        branch    = audit.branch
        warehouse = audit.warehouse

        if branch:
            stocks = Stock.objects.filter(
                branch=branch, warehouse__isnull=True
            ).select_related('product')
        else:
            stocks = Stock.objects.filter(
                warehouse=warehouse, branch__isnull=True
            ).select_related('product')

        items_to_create = []
        for stock in stocks:
            items_to_create.append(
                StockAuditItem(
                    audit        = audit,
                    product      = stock.product,
                    expected_qty = stock.quantity,
                    actual_qty   = stock.quantity,   # xodim keyinroq o'zgartiradi
                )
            )

        if items_to_create:
            StockAuditItem.objects.bulk_create(items_to_create)

        location_name = branch.name if branch else warehouse.name
        AuditLog.objects.create(
            actor=self.request.user,
            action=AuditLog.Action.CREATE,
            target_model='StockAudit',
            target_id=audit.id,
            description=(
                f"Inventarizatsiya yaratildi (draft): '{location_name}', "
                f"{len(items_to_create)} ta mahsulot"
            ),
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            {
                'message': "Inventarizatsiya muvaffaqiyatli yaratildi. Satrlarni to'ldirib, /confirm/ bilan tasdiqlang.",
                'data': StockAuditDetailSerializer(
                    serializer.instance,
                    context=self.get_serializer_context(),
                ).data,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['post'], url_path='confirm')
    @transaction.atomic
    def confirm(self, request, pk=None):
        """
        Inventarizatsiyani tasdiqlash.

        Jarayon:
          1. Status draft ekanligini tekshirish
          2. Har bir satr uchun diff = actual_qty - expected_qty
             diff > 0 → StockMovement(IN,  qty=diff,     note='Inventarizatsiya: oshiqcha')
             diff < 0 → StockMovement(OUT, qty=abs(diff), note='Inventarizatsiya: kamomad')
             diff == 0 → skip
          3. OUT harakatlar uchun qoldiq yetarliligini avvaldan tekshirish
          4. Stock'larni yangilash + FIFO deduct (OUT uchun)
          5. StockAudit.status = confirmed, confirmed_on = now()
          6. AuditLog
        """
        audit = self.get_object()

        if audit.status != AuditStatus.DRAFT:
            return Response(
                {
                    'error': (
                        f"Faqat 'draft' inventarizatsiyani tasdiqlash mumkin. "
                        f"Hozirgi holat: '{audit.get_status_display()}'."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        items = list(audit.items.select_related('product').all())
        if not items:
            return Response(
                {'error': "Inventarizatsiya bo'sh — hech qanday mahsulot yo'q."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        branch    = audit.branch
        warehouse = audit.warehouse
        worker    = getattr(request.user, 'worker', None)
        store     = getattr(worker, 'store', None)

        # ── QADAM 1: OUT bo'ladigan satrlar uchun qoldiq tekshirish ─────────
        errors = []
        for item in items:
            diff = item.actual_qty - item.expected_qty
            if diff < 0:
                abs_diff = abs(diff)
                if branch:
                    stock, _ = Stock.objects.select_for_update().get_or_create(
                        product=item.product, branch=branch, warehouse=None,
                        defaults={'quantity': 0},
                    )
                else:
                    stock, _ = Stock.objects.select_for_update().get_or_create(
                        product=item.product, branch=None, warehouse=warehouse,
                        defaults={'quantity': 0},
                    )
                if stock.quantity < abs_diff:
                    errors.append(
                        f"'{item.product.name}': qoldiq yetarli emas "
                        f"({stock.quantity} bor, {abs_diff} chiqim kerak)."
                    )

        if errors:
            return Response(
                {'errors': errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ── QADAM 2: Har bir satr uchun harakat va stock yangilash ──────────
        for item in items:
            diff = item.actual_qty - item.expected_qty
            if diff == 0:
                continue

            movement_type = MovementType.IN if diff > 0 else MovementType.OUT
            qty           = abs(diff)
            note_text     = (
                'Inventarizatsiya: oshiqcha' if diff > 0 else 'Inventarizatsiya: kamomad'
            )

            movement = StockMovement.objects.create(
                product       = item.product,
                branch        = branch,
                warehouse     = warehouse,
                movement_type = movement_type,
                quantity      = qty,
                unit_cost     = item.product.purchase_price,
                note          = note_text,
                worker        = worker,
            )

            # Stock yangilash (F() — atomic)
            if branch:
                stock, _ = Stock.objects.select_for_update().get_or_create(
                    product=item.product, branch=branch, warehouse=None,
                    defaults={'quantity': 0},
                )
            else:
                stock, _ = Stock.objects.select_for_update().get_or_create(
                    product=item.product, branch=None, warehouse=warehouse,
                    defaults={'quantity': 0},
                )

            if movement_type == MovementType.IN:
                Stock.objects.filter(pk=stock.pk).update(
                    quantity=F('quantity') + qty,
                    updated_on=timezone.now(),
                )
                # FIFO: IN partiya yaratish
                if store:
                    from .utils import generate_batch_code
                    batch_code = generate_batch_code(store)
                    StockBatch.objects.create(
                        batch_code   = batch_code,
                        product      = item.product,
                        branch       = branch,
                        warehouse    = warehouse,
                        unit_cost    = item.product.purchase_price or 0,
                        qty_received = qty,
                        qty_left     = qty,
                        movement     = movement,
                        store        = store,
                    )
            else:
                Stock.objects.filter(pk=stock.pk).update(
                    quantity=F('quantity') - qty,
                    updated_on=timezone.now(),
                )
                # FIFO: OUT partiyalardan yechib olish
                if store:
                    loc_kwargs = {'branch': branch, 'warehouse': warehouse}
                    deductions, total_cost = fifo_deduct(item.product, loc_kwargs, qty)
                    if qty > 0 and deductions:
                        avg_cost = total_cost / qty
                        StockMovement.objects.filter(pk=movement.pk).update(unit_cost=avg_cost)

        # ── QADAM 3: Audit holati yangilash ─────────────────────────────────
        audit.status       = AuditStatus.CONFIRMED
        audit.confirmed_on = timezone.now()
        audit.save(update_fields=['status', 'confirmed_on'])

        location_name = branch.name if branch else warehouse.name
        AuditLog.objects.create(
            actor=request.user,
            action=AuditLog.Action.UPDATE,
            target_model='StockAudit',
            target_id=audit.id,
            description=(
                f"Inventarizatsiya tasdiqlandi: '{location_name}', "
                f"{len(items)} ta mahsulot tekshirildi"
            ),
        )

        return Response(
            {
                'message': "Inventarizatsiya tasdiqlandi.",
                'data': StockAuditDetailSerializer(
                    audit,
                    context=self.get_serializer_context(),
                ).data,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=['post'], url_path='cancel')
    def cancel(self, request, pk=None):
        """
        Inventarizatsiyani bekor qilish.
        Faqat 'draft' holatdagi inventarizatsiyani bekor qilish mumkin.
        Stock o'zgarmaydi.
        """
        audit = self.get_object()

        if audit.status != AuditStatus.DRAFT:
            return Response(
                {
                    'error': (
                        f"Faqat 'draft' inventarizatsiyani bekor qilish mumkin. "
                        f"Hozirgi holat: '{audit.get_status_display()}'."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        audit.status = AuditStatus.CANCELLED
        audit.save(update_fields=['status'])

        location_name = audit.branch.name if audit.branch_id else audit.warehouse.name
        AuditLog.objects.create(
            actor=request.user,
            action=AuditLog.Action.DELETE,
            target_model='StockAudit',
            target_id=audit.id,
            description=f"Inventarizatsiya bekor qilindi: '{location_name}'",
        )

        return Response(
            {
                'message': "Inventarizatsiya bekor qilindi.",
                'data': StockAuditDetailSerializer(
                    audit,
                    context=self.get_serializer_context(),
                ).data,
            },
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=['patch'],
        url_path=r'items/(?P<item_id>[^/.]+)',
    )
    def update_item(self, request, pk=None, item_id=None):
        """
        Inventarizatsiya satrini yangilash — actual_qty ni kiritish.

        PATCH /api/v1/warehouse/audits/{id}/items/{item_id}/
        Body: { "actual_qty": 12.500 }

        Faqat DRAFT holatdagi inventarizatsiya satrini yangilash mumkin.
        """
        audit = self.get_object()

        if audit.status != AuditStatus.DRAFT:
            return Response(
                {
                    'error': (
                        f"Faqat 'draft' inventarizatsiya satrini yangilash mumkin. "
                        f"Audit holati: '{audit.get_status_display()}'."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            item = audit.items.get(pk=item_id)
        except StockAuditItem.DoesNotExist:
            return Response(
                {'error': "Bunday inventarizatsiya satri topilmadi."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = StockAuditItemUpdateSerializer(
            item,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        from .serializers import StockAuditItemSerializer
        return Response(
            {
                'message': "Inventarizatsiya satri yangilandi.",
                'data': StockAuditItemSerializer(item).data,
            },
            status=status.HTTP_200_OK,
        )
