from django.contrib import admin

from .models import (
    Category,
    Currency,
    ExchangeRate,
    Product,
    Stock,
    StockMovement,
    SubCategory,
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
    # ExchangeRate: currency, rate, date, source, created_on — store yo'q
    list_display  = ('currency', 'rate', 'date', 'source', 'created_on')
    list_filter   = ('currency',)
    search_fields = ('currency__code',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display  = ('name', 'category', 'unit', 'sale_price', 'store', 'status')
    list_filter   = ('status', 'unit', 'store', 'category')
    search_fields = ('name', 'barcode')


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    # Stock: product, branch, quantity, updated_on — warehouse yo'q
    list_display  = ('product', 'branch', 'quantity', 'updated_on')
    list_filter   = ('branch',)
    search_fields = ('product__name',)


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    # StockMovement: product, branch, movement_type, quantity, worker, created_on
    list_display    = ('product', 'movement_type', 'quantity', 'branch', 'worker', 'created_on')
    list_filter     = ('movement_type', 'branch')
    search_fields   = ('product__name',)
    readonly_fields = ('created_on',)
