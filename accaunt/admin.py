from django.contrib import admin
from .models import CustomUser, Permission, Role, Worker

# Register your models here.

@admin.register(CustomUser)
class CustomUser_Admin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'username', 'phone1', 'status')
    list_filter = ('status', 'created_on')
    search_fields = ('first_name', 'last_name')
    
    
@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    """ Permissionlarni boshqarish """

    list_display = ( "name", "code")
    search_fields = ( "name", "code")
    ordering = ("code",)
    list_per_page = 10


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    """ Ishchi rollari (Admin, Cashier, Manager...) """

    list_display = ("id", "name", "code")
    search_fields = ("name", "code")
    ordering = ("name",)
    filter_horizontal = ("permissions",)
    list_per_page = 10


@admin.register(Worker)
class WorkerAdmin(admin.ModelAdmin):
    """
    Ishchilarni boshqarish
    """

    list_display = ("user", "role", "store", "branch", "salary", "status", "created_on")
    list_filter = ("role", "store", "branch", "status")
    search_fields = ( "user__username", "user__first_name", "user__last_name")
    ordering = ("-created_on",)
    autocomplete_fields = ("user","store","branch","role",)
    readonly_fields = ("created_on",)


