from django.contrib import admin

from .models import (
    Category,
    Currency,
    ExchangeRate,
    Product,
    Stock,
    StockBatch,
    StockMovement,
    SubCategory,
    Transfer,
    TransferItem,
    Warehouse,
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
    list_display  = ('name', 'store', 'address', 'is_active', 'created_on')
    list_filter   = ('is_active', 'store')
    search_fields = ('name', 'address')


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    # Stock: product, branch|warehouse, quantity, updated_on
    list_display  = ('product', 'branch', 'warehouse', 'quantity', 'updated_on')
    list_filter   = ('branch', 'warehouse')
    search_fields = ('product__name',)


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    # StockMovement: product, branch|warehouse, movement_type, quantity, unit_cost, worker, created_on
    list_display    = ('product', 'movement_type', 'quantity', 'unit_cost', 'branch', 'warehouse', 'worker', 'created_on')
    list_filter     = ('movement_type', 'branch', 'warehouse')
    search_fields   = ('product__name',)
    readonly_fields = ('created_on',)


class TransferItemInline(admin.TabularInline):
    model           = TransferItem
    extra           = 0
    readonly_fields = ('product', 'quantity', 'note')
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
    search_fields   = ('id', 'note')
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
