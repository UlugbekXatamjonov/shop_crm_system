from django.contrib import admin

from .models import Category, Product, Stock, StockMovement, Warehouse


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display  = ('name', 'store', 'status', 'created_on')
    list_filter   = ('status', 'store')
    search_fields = ('name',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display  = ('name', 'category', 'unit', 'sale_price', 'store', 'status')
    list_filter   = ('status', 'unit', 'store', 'category')
    search_fields = ('name', 'barcode')


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display  = ('name', 'store', 'address', 'status', 'created_on')
    list_filter   = ('status', 'store')
    search_fields = ('name',)


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display  = ('product', 'branch', 'warehouse', 'quantity', 'updated_on')
    list_filter   = ('branch', 'warehouse')
    search_fields = ('product__name',)


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display  = (
        'product', 'movement_type', 'quantity',
        'from_branch', 'from_warehouse',
        'to_branch', 'to_warehouse',
        'worker', 'created_on',
    )
    list_filter   = ('movement_type',)
    search_fields = ('product__name',)
    readonly_fields = ('created_on',)
