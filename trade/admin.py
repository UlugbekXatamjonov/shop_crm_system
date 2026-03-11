from django.contrib import admin

from .models import Customer, CustomerGroup, Sale, SaleItem, SaleReturn, SaleReturnItem


class SaleItemInline(admin.TabularInline):
    model  = SaleItem
    extra  = 0
    fields = ('product', 'quantity', 'unit_price', 'total_price', 'unit_cost')
    readonly_fields = ('total_price', 'unit_cost')


class SaleReturnItemInline(admin.TabularInline):
    model  = SaleReturnItem
    extra  = 0
    fields = ('product', 'quantity', 'unit_price', 'total_price')
    readonly_fields = ('total_price',)


@admin.register(CustomerGroup)
class CustomerGroupAdmin(admin.ModelAdmin):
    list_display  = ('name', 'store', 'discount', 'created_on')
    list_filter   = ('store',)
    search_fields = ('name',)


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display  = ('name', 'phone', 'store', 'group', 'debt_balance', 'status')
    list_filter   = ('store', 'status', 'group')
    search_fields = ('name', 'phone')


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display   = ('id', 'branch', 'worker', 'payment_type', 'total_price', 'status', 'created_on')
    list_filter    = ('store', 'status', 'payment_type')
    search_fields  = ('id',)
    readonly_fields = ('total_price', 'created_on')
    inlines        = [SaleItemInline]


@admin.register(SaleReturn)
class SaleReturnAdmin(admin.ModelAdmin):
    list_display   = ('id', 'branch', 'worker', 'total_amount', 'status', 'created_on')
    list_filter    = ('store', 'status')
    search_fields  = ('id',)
    readonly_fields = ('total_amount', 'created_on')
    inlines        = [SaleReturnItemInline]
