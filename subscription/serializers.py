"""
============================================================
SUBSCRIPTION — Serializerlar
============================================================
SubscriptionPlanSerializer    — Tarif reja ma'lumotlari
SubscriptionDetailSerializer  — Joriy obuna to'liq
SubscriptionStatusSerializer  — Qisqa holat (har so'rovda tekshirish uchun)
SubscriptionInvoiceSerializer — To'lov tarixi
AdminSubscriptionSerializer   — SuperAdmin uchun kengaytirilgan ko'rinish
AdminInvoiceCreateSerializer  — Admin to'lov qo'shish
AdminSubscriptionUpdateSerializer — Admin obunani o'zgartirish
"""

from datetime import date

from rest_framework import serializers

from .models import (
    Subscription,
    SubscriptionDowngradeLog,
    SubscriptionInvoice,
    SubscriptionPlan,
    SubscriptionStatus,
)


# ============================================================
# TARIF REJA
# ============================================================

class SubscriptionPlanSerializer(serializers.ModelSerializer):
    plan_type_display = serializers.CharField(
        source='get_plan_type_display', read_only=True
    )

    class Meta:
        model  = SubscriptionPlan
        fields = [
            'id', 'plan_type', 'plan_type_display', 'name', 'description',
            'price_monthly', 'price_yearly', 'yearly_discount',
            'max_branches', 'max_warehouses', 'max_workers', 'max_products',
            # Modullar
            'has_subcategory', 'has_sale_return', 'has_wastage',
            'has_stock_audit', 'has_kpi', 'has_price_list',
            'has_multi_currency', 'has_supplier',
            'has_export', 'has_dashboard', 'has_qr_bulk',
            'has_audit_log', 'has_telegram',
        ]


# ============================================================
# OBUNA — EGASI UCHUN
# ============================================================

class SubscriptionStatusSerializer(serializers.ModelSerializer):
    """
    Qisqa holat — har qanday so'rovda qaytarilishi mumkin.
    """
    plan_name     = serializers.CharField(source='plan.name', read_only=True)
    plan_type     = serializers.CharField(source='plan.plan_type', read_only=True)
    status_display= serializers.CharField(source='get_status_display', read_only=True)
    days_left     = serializers.IntegerField(read_only=True)
    is_active     = serializers.BooleanField(read_only=True)

    class Meta:
        model  = Subscription
        fields = [
            'status', 'status_display', 'is_active',
            'plan_name', 'plan_type',
            'end_date', 'days_left',
        ]


class SubscriptionDetailSerializer(serializers.ModelSerializer):
    """
    To'liq obuna ma'lumoti — do'kon egasi uchun.
    """
    plan          = SubscriptionPlanSerializer(read_only=True)
    status_display= serializers.CharField(source='get_status_display', read_only=True)
    days_left     = serializers.IntegerField(read_only=True)
    is_active     = serializers.BooleanField(read_only=True)
    store_name    = serializers.CharField(source='store.name', read_only=True)

    class Meta:
        model  = Subscription
        fields = [
            'id', 'store_name',
            'plan', 'status', 'status_display', 'is_active',
            'is_yearly', 'start_date', 'end_date', 'days_left',
            'last_payment_date', 'last_payment_amount',
            'notified_10d', 'notified_3d', 'notified_1d',
            'created_on', 'updated_on',
        ]


# ============================================================
# TO'LOV TARIXI
# ============================================================

class SubscriptionInvoiceSerializer(serializers.ModelSerializer):
    plan_name  = serializers.CharField(source='plan.name', read_only=True)
    created_by = serializers.SerializerMethodField()
    paid_at    = serializers.DateTimeField(format='%d.%m.%Y %H:%M', read_only=True)

    class Meta:
        model  = SubscriptionInvoice
        fields = [
            'id', 'plan_name', 'amount', 'is_yearly',
            'period_from', 'period_to', 'note',
            'created_by', 'paid_at',
        ]

    def get_created_by(self, obj) -> str:
        if not obj.created_by:
            return "Tizim"
        w = obj.created_by
        return f"{w.user.get_full_name() or w.user.username} ({w.get_role_display()})"


# ============================================================
# SUPERADMIN SERIALIZERLARI
# ============================================================

class AdminSubscriptionSerializer(serializers.ModelSerializer):
    """SuperAdmin uchun — barcha do'konlarni ko'rish."""
    plan_name     = serializers.CharField(source='plan.name', read_only=True)
    plan_type     = serializers.CharField(source='plan.plan_type', read_only=True)
    status_display= serializers.CharField(source='get_status_display', read_only=True)
    days_left     = serializers.IntegerField(read_only=True)
    store_name    = serializers.CharField(source='store.name', read_only=True)
    invoice_count = serializers.SerializerMethodField()

    class Meta:
        model  = Subscription
        fields = [
            'id', 'store', 'store_name',
            'plan', 'plan_name', 'plan_type',
            'status', 'status_display',
            'is_yearly', 'start_date', 'end_date', 'days_left',
            'last_payment_date', 'last_payment_amount',
            'invoice_count', 'created_on', 'updated_on',
        ]

    def get_invoice_count(self, obj) -> int:
        return obj.invoices.count()


class AdminSubscriptionUpdateSerializer(serializers.ModelSerializer):
    """
    SuperAdmin: obunani o'zgartirish.
    Plan, status, sana, is_yearly o'zgartirilishi mumkin.
    """
    class Meta:
        model  = Subscription
        fields = ['plan', 'status', 'is_yearly', 'start_date', 'end_date']

    def validate(self, attrs):
        start = attrs.get('start_date', self.instance.start_date if self.instance else None)
        end   = attrs.get('end_date',   self.instance.end_date   if self.instance else None)
        if start and end and end <= start:
            raise serializers.ValidationError(
                {'end_date': "Tugash sanasi boshlanish sanasidan keyin bo'lishi kerak."}
            )
        return attrs


class AdminInvoiceCreateSerializer(serializers.Serializer):
    """
    SuperAdmin: to'lov qo'shish.
    To'lov qo'shilganda Subscription.end_date avtomatik uzaytiriladi.
    """
    amount      = serializers.DecimalField(max_digits=15, decimal_places=2, min_value=1)
    is_yearly   = serializers.BooleanField(default=False)
    note        = serializers.CharField(max_length=500, required=False, allow_blank=True)

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("To'lov summasi musbat bo'lishi kerak.")
        return value


class AdminExtendSerializer(serializers.Serializer):
    """SuperAdmin: muddatni uzaytirish."""
    days = serializers.IntegerField(min_value=1, max_value=3650)
    note = serializers.CharField(max_length=500, required=False, allow_blank=True)
