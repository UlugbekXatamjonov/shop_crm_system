from django.contrib import admin

from .models import Category, Product, Stock, StockMovement


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


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display  = ('product', 'branch', 'quantity', 'updated_on')
    list_filter   = ('branch',)
    search_fields = ('product__name',)


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display  = ('product', 'branch', 'movement_type', 'quantity', 'worker', 'created_on')
    list_filter   = ('movement_type', 'branch')
    search_fields = ('product__name',)
    readonly_fields = ('created_on',)
