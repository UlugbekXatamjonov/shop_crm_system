from django.contrib import admin

from .models import Customer, CustomerGroup, Sale, SaleItem, SaleReturn, SaleReturnItem


class SaleItemInline(admin.TabularInline):
    model           = SaleItem
    extra           = 0
    fields          = ('product', 'quantity', 'unit_price', 'total_price', 'unit_cost')
    readonly_fields = ('total_price', 'unit_cost')
    can_delete      = False


class SaleReturnItemInline(admin.TabularInline):
    model           = SaleReturnItem
    extra           = 0
    fields          = ('product', 'quantity', 'unit_price', 'total_price')
    readonly_fields = ('total_price',)
    can_delete      = False


@admin.register(CustomerGroup)
class CustomerGroupAdmin(admin.ModelAdmin):
    list_display    = ('name', 'store', 'discount', 'created_on')
    list_filter     = ('store',)
    search_fields   = ('name',)
    ordering        = ('store', 'name')
    readonly_fields = ('created_on',)
    autocomplete_fields = ('store',)


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display    = ('name', 'phone', 'store', 'group', 'debt_balance', 'status', 'created_on')
    list_filter     = ('status', 'store', 'group')
    search_fields   = ('name', 'phone')
    ordering        = ('store', 'name')
    readonly_fields = ('debt_balance', 'created_on')
    autocomplete_fields = ('store', 'group')


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display    = ('id', 'branch', 'worker', 'customer', 'payment_type', 'total_price', 'status', 'created_on')
    list_filter     = ('store', 'status', 'payment_type')
    search_fields   = ('id', 'customer__name', 'customer__phone', 'worker__user__username')
    ordering        = ('-created_on',)
    readonly_fields = ('store', 'branch', 'worker', 'smena', 'total_price', 'created_on')
    date_hierarchy  = 'created_on'
    inlines         = [SaleItemInline]

    fieldsets = (
        ("Asosiy", {
            'fields': ('store', 'branch', 'worker', 'smena', 'customer', 'status')
        }),
        ("To'lov", {
            'fields': ('payment_type', 'total_price', 'discount_amount', 'description')
        }),
        ("Vaqt", {
            'fields': ('created_on',)
        }),
    )


@admin.register(SaleReturn)
class SaleReturnAdmin(admin.ModelAdmin):
    list_display    = ('id', 'branch', 'worker', 'sale', 'total_amount', 'status', 'created_on')
    list_filter     = ('store', 'status')
    search_fields   = ('id', 'sale__id', 'worker__user__username')
    ordering        = ('-created_on',)
    readonly_fields = ('store', 'branch', 'worker', 'smena', 'total_amount', 'created_on')
    date_hierarchy  = 'created_on'
    inlines         = [SaleReturnItemInline]

    fieldsets = (
        ("Asosiy", {
            'fields': ('store', 'branch', 'worker', 'smena', 'sale', 'status')
        }),
        ("Summa", {
            'fields': ('total_amount', 'description')
        }),
        ("Vaqt", {
            'fields': ('created_on',)
        }),
    )
