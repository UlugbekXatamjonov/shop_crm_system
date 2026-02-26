"""
============================================================
ACCAUNT APP — Django Admin konfiguratsiyasi
============================================================
Ro'yxatga olingan modellar:
  - CustomUser  — foydalanuvchilar boshqaruvi
  - Worker      — hodimlar boshqaruvi
  - AuditLog    — tizim amallari jurnali (faqat ko'rish)
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import CustomUser, Worker, AuditLog


# ============================================================
# CUSTOM USER ADMIN
# ============================================================

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """
    Foydalanuvchilarni boshqarish.
    UserAdmin dan voris olinadi — parol hashing saqlanadi.
    """
    list_display  = ('username', 'first_name', 'last_name', 'phone1', 'status', 'created_on')
    list_filter   = ('status', 'is_superuser', 'is_staff', 'created_on')
    search_fields = ('username', 'first_name', 'last_name', 'phone1', 'email')
    ordering      = ('-created_on',)
    readonly_fields = ('created_on',)

    # Standart UserAdmin fieldsets ga phone maydonlari qo'shiladi
    fieldsets = UserAdmin.fieldsets + (
        ("Qo'shimcha ma'lumotlar", {
            'fields': ('phone1', 'phone2', 'status', 'created_on')
        }),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Qo'shimcha ma'lumotlar", {
            'fields': ('first_name', 'last_name', 'phone1', 'phone2')
        }),
    )


# ============================================================
# WORKER ADMIN
# ============================================================

@admin.register(Worker)
class WorkerAdmin(admin.ModelAdmin):
    """
    Hodimlarni boshqarish.
    permissions — to'g'ridan-to'g'ri ruxsatlar ro'yxati (JSONField).
    """
    list_display   = ('user', 'role', 'store', 'branch', 'salary', 'status', 'created_on')
    list_filter    = ('role', 'status', 'store', 'branch')
    search_fields  = ('user__username', 'user__first_name', 'user__last_name')
    ordering       = ('-created_on',)
    readonly_fields = ('created_on',)
    autocomplete_fields = ('user', 'store', 'branch')

    fieldsets = (
        ("Asosiy ma'lumotlar", {
            'fields': ('user', 'role', 'status', 'store', 'branch', 'salary')
        }),
        ("Permission'lar", {
            'fields': ('permissions',),
            'description': (
                "Format: [\"sotuv\", \"ombor\", \"xarajatlar\"]\n"
                "To'liq ro'yxat: boshqaruv, sotuv, dokonlar, ombor, mahsulotlar, "
                "xodimlar, savdolar, xarajatlar, mijozlar, sozlamalar"
            ),
        }),
        ("Vaqt", {
            'fields': ('created_on',)
        }),
    )


# ============================================================
# AUDIT LOG ADMIN
# ============================================================

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """
    Tizim amallari jurnali — faqat ko'rish, o'zgartirish yo'q.
    """
    list_display  = ('actor', 'action', 'target_model', 'target_id', 'created_at')
    list_filter   = ('action', 'target_model', 'created_at')
    search_fields = ('actor__username', 'description', 'target_model')
    ordering      = ('-created_at',)
    readonly_fields = (
        'actor', 'action', 'target_model', 'target_id',
        'description', 'extra_data', 'created_at',
    )

    def has_add_permission(self, request) -> bool:
        """Log yozuvlari faqat tizim tomonidan yaratiladi."""
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        """Log yozuvlarini o'zgartirish mumkin emas."""
        return False
