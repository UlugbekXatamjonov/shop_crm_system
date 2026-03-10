"""
============================================================
STORE APP — View'lar
============================================================
ViewSet'lar:
  StoreViewSet         — Do'konni boshqarish (faqat egasi uchun)
  BranchViewSet        — Filiallarni boshqarish
  StoreSettingsViewSet — Do'kon sozlamalarini boshqarish (BOSQICH 2)
  SmenaViewSet         — Smena (shift) tizimi (BOSQICH 3)

Multi-tenant xavfsizlik:
  Har bir foydalanuvchi faqat o'z do'konining
  ma'lumotlarini ko'ra va boshqara oladi.

StoreSettings qoidalari:
  QOIDA 1: Signal (store/signals.py) — avtomatik yaratiladi
  QOIDA 2: select_related('settings') bilan get_queryset
  QOIDA 3: invalidate_store_settings(store_id) — keshni tozalash

Smena qoidalari:
  - Bir filialda bir vaqtda faqat bitta OPEN smena bo'lishi mumkin
  - shift_enabled=False bo'lsa smena ochib bo'lmaydi
  - require_cash_count=True bo'lsa cash_start/cash_end majburiy
  - X-report: smena yopilmaydi, faqat hisobot qaytariladi
  - Z-report: smena yopiladi + yakuniy hisobot
"""

from django.utils import timezone

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accaunt.models import AuditLog
from accaunt.permissions import CanAccess, IsOwner

from config.cache_utils import get_store_settings, invalidate_store_settings

from .models import Branch, Smena, SmenaStatus, Store, StoreSettings
from .serializers import (
    BranchCreateSerializer,
    BranchDetailSerializer,
    BranchListSerializer,
    BranchUpdateSerializer,
    SmenaCloseSerializer,
    SmenaDetailSerializer,
    SmenaListSerializer,
    SmenaOpenSerializer,
    StoreCreateSerializer,
    StoreDetailSerializer,
    StoreListSerializer,
    StoreSettingsSerializer,
    StoreSettingsUpdateSerializer,
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
      DELETE /api/v1/stores/{id}/  — do'konni o'chirish (faqat owner, hard delete)

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
        return (
            Store.objects
            .filter(id=worker.store.id)
            .select_related('settings')       # QOIDA 2: N+1 query oldini olish
        )

    def perform_create(self, serializer):
        instance = serializer.save()

        # Owner ning worker.store ni yangilash — do'kon yaratilgandan keyin bog'lanadi
        worker = getattr(self.request.user, 'worker', None)
        if worker and worker.store_id is None:
            worker.store = instance
            worker.save(update_fields=['store'])

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
        """Hard delete — do'konni bazadan o'chiradi."""
        AuditLog.objects.create(
            actor=self.request.user,
            action=AuditLog.Action.DELETE,
            target_model='Store',
            target_id=instance.id,
            description=f"Do'kon o'chirildi: '{instance.name}'",
        )
        instance.delete()

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
        if not serializer.validated_data:
            return Response(
                {'message': "Yangilash uchun kamida bitta maydon yuborilishi kerak."},
                status=status.HTTP_400_BAD_REQUEST,
            )
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
            .prefetch_related('workers')  # BranchListSerializer.workers_count uchun
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
        """Hard delete — filialni bazadan o'chiradi."""
        AuditLog.objects.create(
            actor=self.request.user,
            action=AuditLog.Action.DELETE,
            target_model='Branch',
            target_id=instance.id,
            description=f"Filial o'chirildi: '{instance.name}'",
        )
        instance.delete()

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
        if not serializer.validated_data:
            return Response(
                {'message': "Yangilash uchun kamida bitta maydon yuborilishi kerak."},
                status=status.HTTP_400_BAD_REQUEST,
            )
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


# ============================================================
# DO'KON SOZLAMALARI VIEWSET — BOSQICH 2
# ============================================================

class StoreSettingsViewSet(viewsets.ModelViewSet):
    """
    Do'kon sozlamalarini boshqarish.

    Endpointlar:
      GET   /api/v1/settings/      — o'z do'koni sozlamalarini ko'rish
      PATCH /api/v1/settings/{id}/ — sozlamalarni yangilash (faqat owner)

    Ruxsatlar:
      GET   → IsAuthenticated + CanAccess('sozlamalar')
      PATCH → IsAuthenticated + IsOwner

    Muhim:
      - create/delete yo'q (signal avtomatik yaratadi, o'chirish mumkin emas)
      - perform_update: Redis keshni tozalaydi (QOIDA 3)
      - get_queryset: QOIDA 2 — select_related('store') bilan
    """
    http_method_names = ['get', 'patch']

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated(), CanAccess('sozlamalar')]
        return [IsAuthenticated(), IsOwner()]

    def get_serializer_class(self):
        if self.action in ('update', 'partial_update'):
            return StoreSettingsUpdateSerializer
        return StoreSettingsSerializer

    def get_queryset(self):
        """
        QOIDA 2: select_related('store') bilan tortish.
        Faqat o'z do'konining sozlamalarini ko'radi.
        """
        worker = getattr(self.request.user, 'worker', None)
        if not worker or not worker.store:
            return StoreSettings.objects.none()
        return (
            StoreSettings.objects
            .filter(store=worker.store)
            .select_related('store')
        )

    def perform_update(self, serializer):
        """
        Sozlamalarni saqlab, Redis keshni tozalaydi.
        QOIDA 3: invalidate_store_settings — keyingi so'rovda DB dan yangi ma'lumot.
        """
        instance = serializer.save()
        # QOIDA 3 — keshni tozalash
        invalidate_store_settings(instance.store_id)
        AuditLog.objects.create(
            actor=self.request.user,
            action=AuditLog.Action.UPDATE,
            target_model='StoreSettings',
            target_id=instance.id,
            description=(
                f"Do'kon sozlamalari yangilandi: '{instance.store.name}'"
            ),
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
                'message': "Do'kon sozlamalari muvaffaqiyatli yangilandi.",
                'data': StoreSettingsSerializer(serializer.instance).data,
            },
            status=status.HTTP_200_OK,
        )


# ============================================================
# SMENA VIEWSET — BOSQICH 3
# ============================================================

class SmenaViewSet(viewsets.ModelViewSet):
    """
    Smena (kassir smenasi) tizimi.

    Endpointlar:
      GET   /api/v1/shifts/                 — smenalar ro'yxati (filter: ?status, ?branch)
      POST  /api/v1/shifts/                 — smena ochish
      GET   /api/v1/shifts/{id}/            — smena to'liq ma'lumoti
      PATCH /api/v1/shifts/{id}/close/      — smena yopish (Z-report qaytariladi)
      GET   /api/v1/shifts/{id}/x-report/   — X-report (smena yopilmaydi)

    Biznes qoidalari:
      - shift_enabled=False → smena ochib bo'lmaydi (403)
      - Bir filialda bir vaqtda faqat bitta OPEN smena (400)
      - require_cash_count=True → cash_start/cash_end majburiy
      - Yopilgan smenani qayta yopib bo'lmaydi (400)

    Multi-tenant: faqat o'z do'konining smenalari ko'rinadi.
    """
    http_method_names = ['get', 'post', 'patch']

    def get_permissions(self):
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == 'list':
            return SmenaListSerializer
        if self.action == 'create':
            return SmenaOpenSerializer
        if self.action == 'close':
            return SmenaCloseSerializer
        return SmenaDetailSerializer

    def get_queryset(self):
        """
        Multi-tenant: faqat o'z do'konining smenalari.
        URL params orqali filter: ?status=open|closed, ?branch=<id>
        """
        worker = getattr(self.request.user, 'worker', None)
        if not worker or not worker.store:
            return Smena.objects.none()

        qs = (
            Smena.objects
            .filter(store=worker.store)
            .select_related('branch', 'store', 'worker_open__user', 'worker_close__user')
        )

        # ?status=open|closed
        status_param = self.request.query_params.get('status')
        if status_param in (SmenaStatus.OPEN, SmenaStatus.CLOSED):
            qs = qs.filter(status=status_param)

        # ?branch=<id>
        branch_param = self.request.query_params.get('branch')
        if branch_param:
            qs = qs.filter(branch_id=branch_param)

        return qs

    # ----------------------------------------------------------
    # CREATE — smena ochish
    # ----------------------------------------------------------

    def perform_create(self, serializer):
        worker   = self.request.user.worker
        settings = get_store_settings(worker.store_id)    # QOIDA 3

        # 1. Smena tizimi yoqilganmi?
        if not settings.shift_enabled:
            raise PermissionDenied("Smena tizimi bu do'konda o'chirilgan.")

        branch = serializer.validated_data['branch']

        # 2. Branch shu do'konga tegishliligini tekshirish
        if branch.store_id != worker.store_id:
            raise ValidationError({
                'branch': "Bu filial sizning do'koningizga tegishli emas."
            })

        # 3. Bu filialda allaqachon ochiq smena bormi?
        if Smena.objects.filter(branch=branch, status=SmenaStatus.OPEN).exists():
            raise ValidationError({
                'branch': "Bu filialda allaqachon ochiq smena mavjud."
            })

        # 4. require_cash_count tekshirish
        if settings.require_cash_count and 'cash_start' not in self.request.data:
            raise ValidationError({
                'cash_start': "Smena ochishda boshlang'ich naqd kiritish majburiy."
            })

        smena = serializer.save(
            store=worker.store,
            worker_open=worker,
            status=SmenaStatus.OPEN,
        )
        AuditLog.objects.create(
            actor=self.request.user,
            action=AuditLog.Action.CREATE,
            target_model='Smena',
            target_id=smena.id,
            description=(
                f"Smena ochildi: filial='{smena.branch.name}', "
                f"naqd={smena.cash_start}"
            ),
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            {
                'message': 'Smena muvaffaqiyatli ochildi.',
                'data': SmenaDetailSerializer(
                    serializer.instance,
                    context=self.get_serializer_context(),
                ).data,
            },
            status=status.HTTP_201_CREATED,
        )

    # ----------------------------------------------------------
    # CLOSE action — smena yopish (Z-report)
    # ----------------------------------------------------------

    @action(methods=['patch'], detail=True, url_path='close')
    def close(self, request, pk=None):
        """
        Smenani yopadi va Z-report qaytaradi.

        PATCH /api/v1/shifts/{id}/close/
        Body: {"cash_end": 500000, "note": "..."}  — ixtiyoriy

        Javob:
          message   — tasdiqlash xabari
          data      — yangilangan smena ma'lumoti
          z_report  — yakuniy hisobot (BOSQICH 4/6 da to'ldiriladi)
        """
        smena    = self.get_object()
        worker   = request.user.worker
        settings = get_store_settings(worker.store_id)

        # 1. Allaqachon yopilganmi?
        if smena.status == SmenaStatus.CLOSED:
            raise ValidationError({'detail': "Smena allaqachon yopilgan."})

        # 2. Serializer validatsiya
        serializer = SmenaCloseSerializer(smena, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        # 3. require_cash_count: cash_end majburiy
        if settings.require_cash_count and 'cash_end' not in request.data:
            raise ValidationError({
                'cash_end': "Smena yopishda yakuniy naqd kiritish majburiy."
            })

        # 4. Yopish
        smena = serializer.save(
            worker_close=worker,
            end_time=timezone.now(),
            status=SmenaStatus.CLOSED,
        )
        AuditLog.objects.create(
            actor=self.request.user,
            action=AuditLog.Action.UPDATE,
            target_model='Smena',
            target_id=smena.id,
            description=(
                f"Smena yopildi: filial='{smena.branch.name}', "
                f"naqd={smena.cash_end}"
            ),
        )
        return Response(
            {
                'message': 'Smena muvaffaqiyatli yopildi.',
                'data': SmenaDetailSerializer(
                    smena,
                    context=self.get_serializer_context(),
                ).data,
                'z_report': self._build_report(smena),
            },
            status=status.HTTP_200_OK,
        )

    # ----------------------------------------------------------
    # X-REPORT action — smena yopilmaydi
    # ----------------------------------------------------------

    @action(methods=['get'], detail=True, url_path='x-report')
    def x_report(self, request, pk=None):
        """
        X-report: smena davomidagi joriy hisobot. Smena yopilmaydi.

        GET /api/v1/shifts/{id}/x-report/

        Javob:
          smena    — smena ma'lumoti
          x_report — joriy hisobot (BOSQICH 4/6 da to'ldiriladi)
        """
        smena = self.get_object()
        return Response(
            {
                'smena':    SmenaDetailSerializer(
                    smena,
                    context=self.get_serializer_context(),
                ).data,
                'x_report': self._build_report(smena),
            },
            status=status.HTTP_200_OK,
        )

    # ----------------------------------------------------------
    # Report quruvchan yordamchi — BOSQICH 4/6 da to'ldiriladi
    # ----------------------------------------------------------

    def _build_report(self, smena: Smena) -> dict:
        """
        X/Z report ma'lumotlarini quriladi.
        Lazy import ishlatiladi — trade.models dan circular import oldini olish uchun.

        ⚠️ BOSQICH 6 da: Expense modeli qo'shilgandan keyin
              expenses_total to'ldiriladi.
        """
        # Lazy import — trade → store circular import ni oldini oladi
        from django.db.models import Sum, Count
        from trade.models import Sale, SaleStatus, PaymentType

        completed_sales = Sale.objects.filter(
            smena=smena,
            status=SaleStatus.COMPLETED,
        )

        # Umumiy ko'rsatkichlar
        agg = completed_sales.aggregate(
            total=Sum('total_price'),
            count=Count('id'),
        )
        sales_total = agg['total'] or 0
        sales_count = agg['count'] or 0

        # To'lov turi bo'yicha
        def _sum_by_payment(ptype):
            result = completed_sales.filter(payment_type=ptype).aggregate(
                s=Sum('paid_amount')
            )['s']
            return str(result or '0.00')

        # MIXED savdolarda naqd va karta qismi alohida saqlanmaydi —
        # paid_amount umumiy to'langan summa sifatida ko'rsatiladi.
        by_payment = {
            'cash':  _sum_by_payment(PaymentType.CASH),
            'card':  _sum_by_payment(PaymentType.CARD),
            'mixed': _sum_by_payment(PaymentType.MIXED),
            'debt':  _sum_by_payment(PaymentType.DEBT),
        }

        return {
            'period': {
                'start': smena.start_time.strftime('%Y-%m-%d | %H:%M'),
                'end': (
                    smena.end_time.strftime('%Y-%m-%d | %H:%M')
                    if smena.end_time else None
                ),
            },
            'sales_count':    sales_count,
            'sales_total':    str(sales_total),
            'by_payment':     by_payment,
            # --- BOSQICH 6 da to'ldiriladi ---
            'expenses_total': '0.00',
            # --- Naqd hisobi ---
            'cash_start': str(smena.cash_start),
            'cash_end': (
                str(smena.cash_end)
                if smena.cash_end is not None else None
            ),
        }
