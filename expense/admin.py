from django.contrib import admin

from .models import Expense, ExpenseCategory


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display    = ('name', 'store', 'status', 'created_on')
    list_filter     = ('status', 'store')
    search_fields   = ('name',)
    ordering        = ('store', 'name')
    readonly_fields = ('created_on',)


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display    = ('id', 'category', 'branch', 'worker', 'amount', 'date', 'created_on')
    list_filter     = ('store', 'category', 'branch')
    search_fields   = ('description', 'worker__user__username')
    ordering        = ('-date', '-created_on')
    date_hierarchy  = 'date'
    readonly_fields = ('store', 'branch', 'worker', 'smena', 'created_on')

    fieldsets = (
        ("Asosiy", {
            'fields': ('store', 'branch', 'worker', 'smena', 'category')
        }),
        ("Summa", {
            'fields': ('amount', 'date', 'description')
        }),
        ("Vaqt", {
            'fields': ('created_on',)
        }),
    )
