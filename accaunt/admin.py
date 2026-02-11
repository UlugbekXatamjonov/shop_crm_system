from django.contrib import admin
from .models import CustomUser

# Register your models here.

@admin.register(CustomUser)
class CustomUser_Admin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'username', 'phone1', 'status')
    list_filter = ('status', 'created_on')
    