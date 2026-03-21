from django.contrib import admin

from config.cache_utils import invalidate_subscription_cache

from .models import (
    Subscription, SubscriptionDowngradeLog, SubscriptionInvoice, SubscriptionPlan,
)


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display    = (
        'name', 'plan_type', 'price_monthly',
        'max_branches', 'max_workers', 'max_products',
        'has_dashboard', 'has_export',
    )
    list_filter     = ('plan_type', 'has_dashboard', 'has_export')
    search_fields   = ('name',)
    ordering        = ('plan_type', 'price_monthly')

    fieldsets = (
        ("Asosiy", {
            'fields': ('name', 'plan_type', 'price_monthly')
        }),
        ("Cheklovlar", {
            'fields': ('max_branches', 'max_workers', 'max_products')
        }),
        ("Xususiyatlar", {
            'fields': ('has_dashboard', 'has_export')
        }),
    )


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display    = ('store', 'plan', 'status', 'start_date', 'end_date')
    list_filter     = ('status', 'plan')
    search_fields   = ('store__name',)
    ordering        = ('-end_date',)
    readonly_fields = ('store',)
    autocomplete_fields = ('plan',)
    date_hierarchy  = 'end_date'

    fieldsets = (
        ("Do'kon", {
            'fields': ('store', 'plan', 'status')
        }),
        ("Muddat", {
            'fields': ('start_date', 'end_date')
        }),
    )

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        invalidate_subscription_cache(obj.store_id)


@admin.register(SubscriptionInvoice)
class SubscriptionInvoiceAdmin(admin.ModelAdmin):
    list_display    = ('id', 'subscription', 'amount', 'description', 'paid_at')
    list_filter     = ('subscription__plan',)
    search_fields   = ('subscription__store__name', 'description')
    ordering        = ('-paid_at',)
    readonly_fields = ('paid_at',)
    date_hierarchy  = 'paid_at'


@admin.register(SubscriptionDowngradeLog)
class SubscriptionDowngradeLogAdmin(admin.ModelAdmin):
    list_display    = ('subscription', 'object_type', 'object_id', 'previous_status', 'deactivated_at')
    list_filter     = ('object_type',)
    search_fields   = ('subscription__store__name',)
    ordering        = ('-deactivated_at',)
    readonly_fields = ('subscription', 'object_type', 'object_id', 'previous_status', 'deactivated_at')
    date_hierarchy  = 'deactivated_at'

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False
