from django.contrib import admin

from .models import Expense, ExpenseCategory


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display  = ('name', 'store', 'status', 'created_on')
    list_filter   = ('store', 'status')
    search_fields = ('name',)


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display   = ('id', 'category', 'branch', 'worker', 'amount', 'date', 'created_on')
    list_filter    = ('store', 'category', 'branch')
    search_fields  = ('description',)
    date_hierarchy = 'date'
    readonly_fields = ('created_on',)
