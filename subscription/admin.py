from django.contrib import admin
from .models import SubscriptionPlan, Subscription, SubscriptionInvoice, SubscriptionDowngradeLog
from config.cache_utils import invalidate_subscription_cache


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'plan_type', 'price_monthly', 'max_branches', 'max_workers', 'max_products', 'has_dashboard', 'has_export']
    list_filter  = ['plan_type']


class SubscriptionInvoiceInline(admin.TabularInline):
    model         = SubscriptionInvoice
    extra         = 0
    readonly_fields = ['amount', 'paid_at']


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display  = ['store', 'plan', 'status', 'start_date', 'end_date']
    list_filter   = ['status', 'plan']
    search_fields = ['store__name']
    inlines       = [SubscriptionInvoiceInline]

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        invalidate_subscription_cache(obj.store_id)


@admin.register(SubscriptionInvoice)
class SubscriptionInvoiceAdmin(admin.ModelAdmin):
    list_display    = ['subscription', 'amount', 'paid_at']
    readonly_fields = ['paid_at']


@admin.register(SubscriptionDowngradeLog)
class SubscriptionDowngradeLogAdmin(admin.ModelAdmin):
    list_display    = ['subscription', 'object_type', 'object_id', 'previous_status', 'deactivated_at']
    readonly_fields = ['deactivated_at']
