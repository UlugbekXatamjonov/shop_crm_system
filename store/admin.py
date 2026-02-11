from django.contrib import admin
from .models import Branch, Store
# Register your models here.


@admin.register(Store)
class Store_Admin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(Branch)
class Branch_Admin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

    
    
    