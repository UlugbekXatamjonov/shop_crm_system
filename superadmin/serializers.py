from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers

from store.models import Store
from subscription.models import Subscription, SubscriptionInvoice, SubscriptionPlan
from .models import AdminExpense, Coupon, CouponUsage

User = get_user_model()


# ============================================================
# DO'KONLAR
# ============================================================

class StoreListSerializer(serializers.ModelSerializer):
    plan_name        = serializers.SerializerMethodField()
    subscription_status = serializers.SerializerMethodField()
    days_left        = serializers.SerializerMethodField()
    workers_count    = serializers.SerializerMethodField()
    health_score     = serializers.SerializerMethodField()

    class Meta:
        model  = Store
        fields = [
            'id', 'name', 'address', 'phone', 'status',
            'plan_name', 'subscription_status', 'days_left',
            'workers_count', 'health_score', 'created_on',
        ]

    def get_plan_name(self, obj):
        try:
            return obj.subscription.plan.name
        except Exception:
            return None

    def get_subscription_status(self, obj):
        try:
            return obj.subscription.status
        except Exception:
            return None

    def get_days_left(self, obj):
        try:
            return obj.subscription.days_left
        except Exception:
            return None

    def get_workers_count(self, obj):
        return obj.workers.filter(status='active').count()

    def get_health_score(self, obj):
        from trade.models import Sale
        last_7  = Sale.objects.filter(store=obj, created_on__gte=timezone.now() - timezone.timedelta(days=7)).count()
        last_30 = Sale.objects.filter(store=obj, created_on__gte=timezone.now() - timezone.timedelta(days=30)).count()
        total   = Sale.objects.filter(store=obj).count()
        if total == 0:
            return 'dead'
        if last_7 >= 10:
            return 'very_active'
        if last_30 >= 1:
            return 'moderate'
        return 'sleeping'


class OnboardingSerializer(serializers.Serializer):
    store_configured  = serializers.BooleanField()
    first_product     = serializers.BooleanField()
    first_worker      = serializers.BooleanField()
    first_sale        = serializers.BooleanField()
    first_shift       = serializers.BooleanField()
    warehouse_stocked = serializers.BooleanField()


class StoreDetailSerializer(serializers.ModelSerializer):
    plan_name           = serializers.SerializerMethodField()
    subscription_status = serializers.SerializerMethodField()
    subscription_id     = serializers.SerializerMethodField()
    days_left           = serializers.SerializerMethodField()
    end_date            = serializers.SerializerMethodField()
    workers_count       = serializers.SerializerMethodField()
    products_count      = serializers.SerializerMethodField()
    total_sales         = serializers.SerializerMethodField()
    health_score        = serializers.SerializerMethodField()
    onboarding          = serializers.SerializerMethodField()

    class Meta:
        model  = Store
        fields = [
            'id', 'name', 'address', 'phone', 'status', 'created_on',
            'subscription_id', 'plan_name', 'subscription_status',
            'days_left', 'end_date',
            'workers_count', 'products_count', 'total_sales',
            'health_score', 'onboarding',
        ]

    def get_plan_name(self, obj):
        try:
            return obj.subscription.plan.name
        except Exception:
            return None

    def get_subscription_status(self, obj):
        try:
            return obj.subscription.status
        except Exception:
            return None

    def get_subscription_id(self, obj):
        try:
            return obj.subscription.id
        except Exception:
            return None

    def get_days_left(self, obj):
        try:
            return obj.subscription.days_left
        except Exception:
            return None

    def get_end_date(self, obj):
        try:
            return obj.subscription.end_date
        except Exception:
            return None

    def get_workers_count(self, obj):
        return obj.workers.filter(status='active').count()

    def get_products_count(self, obj):
        from warehouse.models import Product
        return Product.objects.filter(store=obj).count()

    def get_total_sales(self, obj):
        from trade.models import Sale
        return Sale.objects.filter(store=obj).count()

    def get_health_score(self, obj):
        from trade.models import Sale
        last_7  = Sale.objects.filter(store=obj, created_on__gte=timezone.now() - timezone.timedelta(days=7)).count()
        last_30 = Sale.objects.filter(store=obj, created_on__gte=timezone.now() - timezone.timedelta(days=30)).count()
        total   = Sale.objects.filter(store=obj).count()
        if total == 0:
            return 'dead'
        if last_7 >= 10:
            return 'very_active'
        if last_30 >= 1:
            return 'moderate'
        return 'sleeping'

    def get_onboarding(self, obj):
        from warehouse.models import Product, Stock
        from trade.models import Sale
        from store.models import Smena
        first_product  = Product.objects.filter(store=obj).exists()
        first_worker   = obj.workers.filter(status='active').count() > 1
        first_sale     = Sale.objects.filter(store=obj).exists()
        first_shift    = Smena.objects.filter(store=obj).exists()
        warehouse_stock = Stock.objects.filter(store=obj, quantity__gt=0).exists()
        return {
            'store_configured':  bool(obj.address or obj.phone),
            'first_product':     first_product,
            'first_worker':      first_worker,
            'first_sale':        first_sale,
            'first_shift':       first_shift,
            'warehouse_stocked': warehouse_stock,
        }


# ============================================================
# OBUNALAR
# ============================================================

class AdminSubscriptionListSerializer(serializers.ModelSerializer):
    store_name = serializers.CharField(source='store.name', read_only=True)
    plan_name  = serializers.CharField(source='plan.name', read_only=True)
    days_left  = serializers.IntegerField(read_only=True)

    class Meta:
        model  = Subscription
        fields = [
            'id', 'store_name', 'plan_name', 'status',
            'start_date', 'end_date', 'days_left',
            'is_yearly', 'last_payment_date', 'last_payment_amount',
            'created_on',
        ]


class AdminSubscriptionDetailSerializer(serializers.ModelSerializer):
    store_name = serializers.CharField(source='store.name', read_only=True)
    store_id   = serializers.IntegerField(source='store.id', read_only=True)
    plan_name  = serializers.CharField(source='plan.name', read_only=True)
    days_left  = serializers.IntegerField(read_only=True)

    class Meta:
        model  = Subscription
        fields = [
            'id', 'store_id', 'store_name', 'plan_name', 'status',
            'start_date', 'end_date', 'days_left',
            'is_yearly', 'last_payment_date', 'last_payment_amount',
            'notified_10d', 'notified_3d', 'notified_1d',
            'created_on', 'updated_on',
        ]


class ExtendSubscriptionSerializer(serializers.Serializer):
    days = serializers.IntegerField(min_value=1, max_value=3650)
    note = serializers.CharField(max_length=500, required=False, allow_blank=True)


class ChangePlanSerializer(serializers.Serializer):
    plan_id = serializers.IntegerField()
    note    = serializers.CharField(max_length=500, required=False, allow_blank=True)

    def validate_plan_id(self, value):
        if not SubscriptionPlan.objects.filter(id=value).exists():
            raise serializers.ValidationError("Tarif topilmadi.")
        return value


class GiveTrialSerializer(serializers.Serializer):
    days = serializers.IntegerField(min_value=1, max_value=365)
    note = serializers.CharField(max_length=500, required=False, allow_blank=True)


# ============================================================
# KUPONLAR
# ============================================================

class CouponListSerializer(serializers.ModelSerializer):
    plan_name      = serializers.CharField(source='plan.name', read_only=True)
    usages_count   = serializers.SerializerMethodField()
    is_valid_now   = serializers.SerializerMethodField()

    class Meta:
        model  = Coupon
        fields = [
            'id', 'code', 'type', 'value', 'max_uses', 'used_count',
            'valid_from', 'valid_to', 'for_new_only', 'plan_name',
            'is_active', 'usages_count', 'is_valid_now', 'created_on',
        ]

    def get_usages_count(self, obj):
        return obj.usages.count()

    def get_is_valid_now(self, obj):
        now = timezone.now()
        return (
            obj.is_active
            and obj.valid_from <= now <= obj.valid_to
            and not obj.is_exhausted
        )


class CouponDetailSerializer(serializers.ModelSerializer):
    plan_name    = serializers.CharField(source='plan.name', read_only=True)
    is_valid_now = serializers.SerializerMethodField()
    is_exhausted = serializers.BooleanField(read_only=True)

    class Meta:
        model  = Coupon
        fields = [
            'id', 'code', 'type', 'value', 'max_uses', 'used_count',
            'valid_from', 'valid_to', 'for_new_only', 'plan', 'plan_name',
            'is_active', 'description', 'is_valid_now', 'is_exhausted',
            'created_on',
        ]

    def get_is_valid_now(self, obj):
        now = timezone.now()
        return (
            obj.is_active
            and obj.valid_from <= now <= obj.valid_to
            and not obj.is_exhausted
        )


class CouponCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Coupon
        fields = [
            'code', 'type', 'value', 'max_uses',
            'valid_from', 'valid_to', 'for_new_only', 'plan',
            'is_active', 'description',
        ]

    def validate(self, attrs):
        if attrs.get('valid_from') and attrs.get('valid_to'):
            if attrs['valid_from'] >= attrs['valid_to']:
                raise serializers.ValidationError(
                    {"valid_to": "Tugash sanasi boshlanish sanasidan keyin bo'lishi kerak."}
                )
        if attrs.get('value', 0) <= 0:
            raise serializers.ValidationError({"value": "Qiymat 0 dan katta bo'lishi kerak."})
        return attrs


class CouponUsageSerializer(serializers.ModelSerializer):
    store_name = serializers.CharField(source='store.name', read_only=True)
    coupon_code = serializers.CharField(source='coupon.code', read_only=True)

    class Meta:
        model  = CouponUsage
        fields = ['id', 'coupon_code', 'store_name', 'applied_at', 'discount_value', 'note']


class ApplyCouponSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=50)


# ============================================================
# ADMIN XARAJATLARI
# ============================================================

class AdminExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model  = AdminExpense
        fields = ['id', 'title', 'category', 'amount', 'date', 'note', 'created_on']
        read_only_fields = ['created_on']

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Summa 0 dan katta bo'lishi kerak.")
        return value


# ============================================================
# TARIF REJALARI (superadmin boshqaruvi)
# ============================================================

class AdminPlanSerializer(serializers.ModelSerializer):
    active_subscriptions = serializers.SerializerMethodField()
    monthly_revenue      = serializers.SerializerMethodField()

    class Meta:
        model  = SubscriptionPlan
        fields = [
            'id', 'plan_type', 'name', 'description',
            'price_monthly', 'price_yearly', 'yearly_discount',
            'max_branches', 'max_warehouses', 'max_workers', 'max_products',
            'has_subcategory', 'has_sale_return', 'has_wastage',
            'has_stock_audit', 'has_kpi', 'has_multi_currency',
            'has_supplier', 'has_export', 'has_dashboard',
            'has_qr_bulk', 'has_audit_log', 'has_telegram',
            'active_subscriptions', 'monthly_revenue',
            'created_on', 'updated_on',
        ]

    def get_active_subscriptions(self, obj):
        return obj.subscriptions.filter(status__in=['trial', 'active']).count()

    def get_monthly_revenue(self, obj):
        count = obj.subscriptions.filter(status='active').count()
        return float(obj.price_monthly) * count
