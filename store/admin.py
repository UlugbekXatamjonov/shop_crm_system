from django.contrib import admin

from .models import Branch, Smena, Store, StoreSettings


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display    = ('name', 'phone', 'status', 'created_on')
    list_filter     = ('status',)
    search_fields   = ('name', 'phone', 'address')
    ordering        = ('name',)
    readonly_fields = ('created_on',)


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display    = ('name', 'store', 'phone', 'status', 'created_on')
    list_filter     = ('status', 'store')
    search_fields   = ('name', 'phone', 'address', 'store__name')
    ordering        = ('store', 'name')
    readonly_fields = ('created_on',)
    autocomplete_fields = ('store',)


@admin.register(StoreSettings)
class StoreSettingsAdmin(admin.ModelAdmin):
    list_display  = (
        'store', 'default_currency',
        'shift_enabled', 'sale_return_enabled', 'wastage_enabled',
        'kpi_enabled', 'has_export',
    )
    list_filter   = ('shift_enabled', 'sale_return_enabled', 'default_currency')
    search_fields = ('store__name',)
    readonly_fields = ('store',)

    def has_export(self, obj):
        return obj.store.subscription.plan.has_export if hasattr(obj.store, 'subscription') else '—'
    has_export.short_description = 'Export'

    fieldsets = (
        ("Do'kon", {'fields': ('store',)}),
        ("Funksiyalar", {
            'fields': (
                'subcategory_enabled', 'sale_return_enabled', 'wastage_enabled',
                'stock_audit_enabled', 'kpi_enabled', 'price_list_enabled',
            )
        }),
        ("To'lov", {
            'fields': ('allow_cash', 'allow_card', 'allow_debt', 'allow_discount', 'max_discount_percent')
        }),
        ("Valyuta", {
            'fields': ('default_currency', 'show_usd_price', 'show_rub_price', 'show_eur_price', 'show_cny_price')
        }),
        ("Chek", {
            'fields': ('receipt_header', 'receipt_footer', 'show_store_logo', 'show_worker_name')
        }),
        ("Smena", {
            'fields': ('shift_enabled', 'shifts_per_day', 'require_cash_count', 'auto_pdf_on_smena_close')
        }),
        ("Kam qoldiq ogohlantirish", {
            'fields': ('low_stock_enabled', 'low_stock_threshold')
        }),
        ("Soliq", {
            'fields': ('tax_enabled', 'tax_percent')
        }),
        ("Telegram", {
            'fields': ('telegram_enabled', 'telegram_chat_id')
        }),
        ("OFD", {
            'fields': ('ofd_enabled', 'ofd_token', 'ofd_device_id')
        }),
        ("Yetkazib beruvchi kredit", {
            'fields': ('supplier_credit_enabled',)
        }),
    )


@admin.register(Smena)
class SmenaAdmin(admin.ModelAdmin):
    list_display    = (
        'id', 'branch', 'status',
        'worker_open', 'worker_close',
        'cash_start', 'cash_end',
        'start_time', 'end_time',
    )
    list_filter     = ('status', 'branch__store', 'branch')
    search_fields   = ('branch__name', 'branch__store__name')
    ordering        = ('-start_time',)
    readonly_fields = (
        'store', 'branch', 'status',
        'worker_open', 'worker_close',
        'start_time', 'end_time',
        'cash_start', 'cash_end',
    )
    date_hierarchy  = 'start_time'
