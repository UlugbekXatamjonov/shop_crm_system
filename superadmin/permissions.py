from rest_framework.permissions import BasePermission


class IsSuperAdmin(BasePermission):
    """
    Faqat is_superuser=True bo'lgan foydalanuvchilar kirishi mumkin.
    """
    message = "Bu endpoint faqat superadmin uchun."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_superuser
        )
