"""
============================================================
SUBSCRIPTION — View'lar
============================================================
DO'KON EGASI uchun:
  GET  /api/v1/subscription/           — joriy obuna holati
  GET  /api/v1/subscription/plans/     — barcha tarif rejalari
  GET  /api/v1/subscription/invoices/  — o'z to'lov tarixi

SUPERADMIN uchun:
  GET    /api/v1/admin/subscriptions/                    — barcha do'konlar
  GET    /api/v1/admin/subscriptions/{id}/               — bitta do'kon
  PATCH  /api/v1/admin/subscriptions/{id}/               — obunani o'zgartirish
  POST   /api/v1/admin/subscriptions/{id}/extend/        — muddatni uzaytirish
  POST   /api/v1/admin/subscriptions/{id}/add-invoice/   — to'lov qo'shish
"""

import logging
from datetime import date, timedelta

from django.db import transaction
from django.utils import timezone

from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accaunt.models import AuditLog
from accaunt.audit_mixin import AuditMixin
from accaunt.permissions import IsOwner, IsSuperAdmin

from config.cache_utils import invalidate_subscription_cache

from .models import (
    Subscription,
    SubscriptionInvoice,
    SubscriptionPlan,
    SubscriptionStatus,
)
from .serializers import (
    AdminExtendSerializer,
    AdminInvoiceCreateSerializer,
    AdminSubscriptionSerializer,
    AdminSubscriptionUpdateSerializer,
    SubscriptionDetailSerializer,
    SubscriptionInvoiceSerializer,
    SubscriptionPlanSerializer,
)
from .utils import apply_lifo_deactivation, reactivate_downgraded_objects

logger = logging.getLogger(__name__)


# ============================================================
# DO'KON EGASI — O'Z OBUNASINI KO'RISH
# ============================================================

class MySubscriptionView(APIView):
    """
    Joriy obuna holati.

    GET /api/v1/subscription/
    Ruxsat: IsOwner
    """
    permission_classes = [IsAuthenticated, IsOwner]

    def get(self, request):
        worker = request.user.worker
        try:
            sub = Subscription.objects.select_related('plan', 'store').get(
                store=worker.store
            )
        except Subscription.DoesNotExist:
            return Response(
                {'detail': "Obuna topilmadi. Admin bilan bog'laning."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(SubscriptionDetailSerializer(sub).data)


class PlanListView(APIView):
    """
    Barcha tarif rejalari ro'yxati.

    GET /api/v1/subscription/plans/
    Ruxsat: IsAuthenticated (barcha rollar ko'ra oladi)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        plans = SubscriptionPlan.objects.all().order_by('price_monthly')
        return Response(SubscriptionPlanSerializer(plans, many=True).data)


class MyInvoiceListView(APIView):
    """
    O'z to'lov tarixi.

    GET /api/v1/subscription/invoices/
    Ruxsat: IsOwner
    """
    permission_classes = [IsAuthenticated, IsOwner]

    def get(self, request):
        worker = request.user.worker
        try:
            sub = Subscription.objects.get(store=worker.store)
        except Subscription.DoesNotExist:
            return Response([])

        invoices = SubscriptionInvoice.objects.filter(
            subscription=sub
        ).select_related('plan', 'created_by', 'created_by__user').order_by('-paid_at')

        return Response(SubscriptionInvoiceSerializer(invoices, many=True).data)


# ============================================================
# SUPERADMIN — BOSHQARUV
# ============================================================

class AdminSubscriptionViewSet(AuditMixin, viewsets.GenericViewSet):
    """
    SuperAdmin: barcha do'konlarning obunalarini boshqarish.

    GET    /api/v1/admin/subscriptions/           — ro'yxat
    GET    /api/v1/admin/subscriptions/{id}/      — bitta
    PATCH  /api/v1/admin/subscriptions/{id}/      — o'zgartirish
    POST   /api/v1/admin/subscriptions/{id}/extend/     — muddat uzaytirish
    POST   /api/v1/admin/subscriptions/{id}/add-invoice/— to'lov qo'shish
    """
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def get_queryset(self):
        return Subscription.objects.select_related(
            'store', 'plan'
        ).order_by('store__name')

    def get_serializer_class(self):
        if self.action == 'partial_update':
            return AdminSubscriptionUpdateSerializer
        return AdminSubscriptionSerializer

    # ---- LIST ----
    def list(self, request):
        qs = self.get_queryset()

        # Filtr: status
        st = request.query_params.get('status')
        if st:
            qs = qs.filter(status=st)

        # Filtr: plan_type
        plan_type = request.query_params.get('plan_type')
        if plan_type:
            qs = qs.filter(plan__plan_type=plan_type)

        return Response(AdminSubscriptionSerializer(qs, many=True).data)

    # ---- RETRIEVE ----
    def retrieve(self, request, pk=None):
        sub = self.get_object()
        return Response(AdminSubscriptionSerializer(sub).data)

    # ---- PATCH (plan/status/sana o'zgartirish) ----
    def partial_update(self, request, pk=None):
        sub         = self.get_object()
        old_plan    = sub.plan
        old_status  = sub.status
        serializer  = AdminSubscriptionUpdateSerializer(
            sub, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            new_plan   = serializer.validated_data.get('plan', old_plan)
            new_status = serializer.validated_data.get('status', old_status)
            serializer.save()
            sub.refresh_from_db()

            # Plan o'zgardimi?
            if new_plan.id != old_plan.id:
                _handle_plan_change(sub, old_plan, new_plan, request)

            # Status active bo'lsa — notif flaglarini reset
            if new_status in (SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL):
                sub.notified_10d = False
                sub.notified_3d  = False
                sub.notified_1d  = False
                sub.save(update_fields=['notified_10d', 'notified_3d', 'notified_1d'])

            invalidate_subscription_cache(sub.store_id)

        self._audit_log(
            AuditLog.Action.UPDATE, sub,
            description=(
                f"Obuna yangilandi: '{sub.store.name}' — "
                f"plan: {new_plan.name}, status: {new_status}"
            )
        )
        return Response({
            'message': "Obuna muvaffaqiyatli yangilandi.",
            'data': AdminSubscriptionSerializer(sub).data,
        })

    # ---- EXTEND (muddat uzaytirish) ----
    @action(methods=['post'], detail=True, url_path='extend')
    def extend(self, request, pk=None):
        """
        POST /api/v1/admin/subscriptions/{id}/extend/
        Body: {"days": 30, "note": "..."}
        """
        sub        = self.get_object()
        serializer = AdminExtendSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        days = serializer.validated_data['days']
        description = serializer.validated_data.get('description', '')

        # end_date uzaytirish (hozirdan kichik bo'lsa hozirdan boshlanadi)
        base_date   = max(sub.end_date, date.today())
        sub.end_date = base_date + timedelta(days=days)

        # Agar expired bo'lsa — active ga o'tkazish
        if sub.status == SubscriptionStatus.EXPIRED:
            sub.status = SubscriptionStatus.ACTIVE

        # Ogohlantirish flaglarini reset
        sub.notified_10d = False
        sub.notified_3d  = False
        sub.notified_1d  = False
        sub.save()

        invalidate_subscription_cache(sub.store_id)

        self._audit_log(
            AuditLog.Action.UPDATE, sub,
            description=(
                f"Obuna muddati uzaytirildi: '{sub.store.name}' — "
                f"+{days} kun, yangi tugash: {sub.end_date}"
                + (f", izoh: {description}" if description else "")
            )
        )
        return Response({
            'message': f"Obuna {days} kunga uzaytirildi.",
            'data': AdminSubscriptionSerializer(sub).data,
        })

    # ---- ADD-INVOICE (to'lov qo'shish) ----
    @action(methods=['post'], detail=True, url_path='add-invoice')
    def add_invoice(self, request, pk=None):
        """
        POST /api/v1/admin/subscriptions/{id}/add-invoice/
        Body: {"amount": 99000, "is_yearly": false, "note": "..."}

        To'lov qo'shilganda:
          1. SubscriptionInvoice yaratiladi
          2. end_date: oylik → +30 kun, yillik → +365 kun
          3. Status active bo'ladi
          4. Ogohlantirish flaglari reset
          5. Downgraded ob'ektlar qaytariladi
        """
        sub        = self.get_object()
        serializer = AdminInvoiceCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        amount    = serializer.validated_data['amount']
        is_yearly = serializer.validated_data['is_yearly']
        description = serializer.validated_data.get('description', '')

        with transaction.atomic():
            # Davr hisoblash
            base_date   = max(sub.end_date, date.today())
            extend_days = 365 if is_yearly else 30
            period_from = base_date
            period_to   = base_date + timedelta(days=extend_days)

            # Invoice yaratish
            invoice = SubscriptionInvoice.objects.create(
                subscription = sub,
                plan         = sub.plan,
                amount       = amount,
                is_yearly    = is_yearly,
                period_from  = period_from,
                period_to    = period_to,
                description  = description,
                created_by   = request.user.worker,
            )

            # Subscription yangilash
            sub.end_date            = period_to
            sub.last_payment_date   = date.today()
            sub.last_payment_amount = amount
            sub.is_yearly           = is_yearly
            sub.status              = SubscriptionStatus.ACTIVE
            sub.notified_10d        = False
            sub.notified_3d         = False
            sub.notified_1d         = False
            sub.save()

            # Expired sababli inactive bo'lgan ob'ektlarni qaytarish
            reactivated = reactivate_downgraded_objects(sub)

            invalidate_subscription_cache(sub.store_id)

        self._audit_log(
            AuditLog.Action.CREATE, invoice,
            description=(
                f"To'lov qo'shildi: '{sub.store.name}' — "
                f"{amount:,.0f} UZS, {'yillik' if is_yearly else 'oylik'}, "
                f"yangi tugash: {sub.end_date}"
            )
        )
        return Response({
            'message':     "To'lov muvaffaqiyatli qo'shildi.",
            'data':        AdminSubscriptionSerializer(sub).data,
            'invoice':     SubscriptionInvoiceSerializer(invoice).data,
            'reactivated': reactivated,
        }, status=status.HTTP_201_CREATED)


# ============================================================
# YORDAMCHI
# ============================================================

def _handle_plan_change(sub, old_plan, new_plan, request) -> None:
    """
    Plan o'zgarganda:
      - Downgrade: LIFO inactive
      - Upgrade: DowngradeLog orqali qaytarish
    """
    # Oddiy taqqoslash: narx bo'yicha (yoki max_products bo'yicha)
    old_value = old_plan.price_monthly
    new_value = new_plan.price_monthly

    if new_value < old_value:
        # Downgrade
        result = apply_lifo_deactivation(sub)
        logger.info("Plan downgrade: store=%s, %s→%s, result=%s",
                    sub.store.id, old_plan.plan_type, new_plan.plan_type, result)
    elif new_value > old_value:
        # Upgrade
        result = reactivate_downgraded_objects(sub)
        logger.info("Plan upgrade: store=%s, %s→%s, result=%s",
                    sub.store.id, old_plan.plan_type, new_plan.plan_type, result)
