from django.contrib import admin

from .models import (
    Category,
    Currency,
    ExchangeRate,
    Product,
    Stock,
    StockAudit,
    StockAuditItem,
    StockBatch,
    StockMovement,
    SubCategory,
    Supplier,
    SupplierPayment,
    Transfer,
    TransferItem,
    Warehouse,
    WastageRecord,
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display  = ('name', 'store', 'status', 'created_on')
    list_filter   = ('status', 'store')
    search_fields = ('name',)


@admin.register(SubCategory)
class SubCategoryAdmin(admin.ModelAdmin):
    list_display  = ('name', 'category', 'store', 'status', 'created_on')
    list_filter   = ('status', 'store', 'category')
    search_fields = ('name',)


@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    # Currency: code, name, symbol, is_base — store va created_on yo'q
    list_display  = ('code', 'name', 'symbol', 'is_base')
    list_filter   = ('is_base',)
    search_fields = ('code', 'name')


@admin.register(ExchangeRate)
class ExchangeRateAdmin(admin.ModelAdmin):
    # ExchangeRate: currency, rate, date, created_on — store yo'q
    list_display  = ('currency', 'rate', 'date', 'created_on')
    list_filter   = ('currency',)
    search_fields = ('currency__code',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display  = ('name', 'category', 'unit', 'sale_price', 'store', 'status')
    list_filter   = ('status', 'unit', 'store', 'category')
    search_fields = ('name', 'barcode')


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display  = ('name', 'store', 'address', 'status', 'created_on')
    list_filter   = ('status', 'store')
    search_fields = ('name', 'address')


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    # Stock: product, branch|warehouse, quantity, updated_on
    list_display  = ('product', 'branch', 'warehouse', 'quantity', 'updated_on')
    list_filter   = ('branch', 'warehouse')
    search_fields = ('product__name',)


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    # StockMovement: product, branch|warehouse, movement_type, quantity, unit_cost, supplier, worker, created_on
    list_display    = ('product', 'movement_type', 'quantity', 'unit_cost', 'supplier', 'branch', 'warehouse', 'worker', 'created_on')
    list_filter     = ('movement_type', 'branch', 'warehouse')
    search_fields   = ('product__name',)
    readonly_fields = ('created_on',)


class TransferItemInline(admin.TabularInline):
    model           = TransferItem
    extra           = 0
    readonly_fields = ('product', 'quantity', 'description')
    can_delete      = False


@admin.register(Transfer)
class TransferAdmin(admin.ModelAdmin):
    list_display    = (
        'id', 'store', 'status',
        'from_branch', 'from_warehouse',
        'to_branch',   'to_warehouse',
        'worker', 'confirmed_at', 'created_on',
    )
    list_filter     = ('status', 'store')
    search_fields   = ('id', 'description')
    readonly_fields = ('status', 'confirmed_at', 'created_on', 'worker')
    inlines         = [TransferItemInline]


@admin.register(StockBatch)
class StockBatchAdmin(admin.ModelAdmin):
    """
    FIFO partiyalar — faqat ko'rish (immutable log).
    qty_left — FIFO da kamayadi, o'zgartirish admin dan mumkin emas.
    """
    list_display    = (
        'batch_code', 'product', 'store',
        'branch', 'warehouse',
        'unit_cost', 'qty_received', 'qty_left',
        'received_at',
    )
    list_filter     = ('store', 'branch', 'warehouse')
    search_fields   = ('batch_code', 'product__name')
    readonly_fields = (
        'batch_code', 'product', 'branch', 'warehouse',
        'unit_cost', 'qty_received', 'movement',
        'store', 'received_at',
    )
    ordering        = ['received_at', 'id']


@admin.register(WastageRecord)
class WastageRecordAdmin(admin.ModelAdmin):
    """
    Isrof yozuvlari — faqat ko'rish (immutable log).
    """
    list_display    = (
        'id', 'product', 'store',
        'branch', 'warehouse',
        'quantity', 'reason', 'date',
        'worker', 'created_on',
    )
    list_filter     = ('reason', 'store', 'branch', 'warehouse')
    search_fields   = ('product__name',)
    readonly_fields = (
        'product', 'branch', 'warehouse', 'store',
        'worker', 'smena', 'quantity', 'reason', 'description',
        'date', 'created_on',
    )
    ordering        = ['-date', '-created_on']


class StockAuditItemInline(admin.TabularInline):
    model           = StockAuditItem
    extra           = 0
    readonly_fields = ('product', 'expected_qty', 'actual_qty')
    can_delete      = False


@admin.register(StockAudit)
class StockAuditAdmin(admin.ModelAdmin):
    """
    Inventarizatsiya — tafsilotlar bilan ko'rish.
    Tasdiqlangan (confirmed) auditlar readonly.
    """
    list_display    = (
        'id', 'store', 'status',
        'branch', 'warehouse',
        'worker', 'created_on', 'confirmed_on',
    )
    list_filter     = ('status', 'store', 'branch', 'warehouse')
    search_fields   = ('id', 'description')
    readonly_fields = ('status', 'confirmed_on', 'created_on', 'worker', 'store')
    inlines         = [StockAuditItemInline]


class SupplierPaymentInline(admin.TabularInline):
    """Yetkazib beruvchi tafsilotida to'lovlar inline ko'rinishi."""
    model           = SupplierPayment
    extra           = 0
    readonly_fields = ('amount', 'payment_type', 'description', 'smena', 'worker', 'created_on')
    can_delete      = False


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    """
    Yetkazib beruvchilar — to'lovlar inline bilan ko'rish.
    Soft delete: status='inactive' ga o'tkazish.
    """
    list_display    = ('name', 'phone', 'company', 'debt_balance', 'status', 'store', 'created_on')
    list_filter     = ('status', 'store')
    search_fields   = ('name', 'phone', 'company')
    readonly_fields = ('debt_balance', 'created_on', 'updated_on')
    inlines         = [SupplierPaymentInline]


@admin.register(SupplierPayment)
class SupplierPaymentAdmin(admin.ModelAdmin):
    """
    Yetkazib beruvchiga to'lovlar — faqat ko'rish (immutable log).
    """
    list_display    = ('id', 'supplier', 'amount', 'payment_type', 'worker', 'smena', 'created_on')
    list_filter     = ('payment_type', 'supplier__store')
    search_fields   = ('supplier__name',)
    readonly_fields = (
        'supplier', 'amount', 'payment_type',
        'description', 'smena', 'worker', 'created_on',
    )
