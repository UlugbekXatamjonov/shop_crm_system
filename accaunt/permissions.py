"""
============================================================
ACCAUNT APP — DRF Custom Permission Klasslari
============================================================
Bu fayl API endpointlari uchun ruxsat tekshiruvchi
permission klasslarini o'z ichiga oladi.

Ishlatilish tartibi (ViewSet da):
    permission_classes = [IsAuthenticated, IsOwner]
    permission_classes = [IsAuthenticated, IsManagerOrAbove]
    permission_classes = [IsAuthenticated, CanAccess('mahsulotlar')]

Ierarxiya:
    SuperAdmin > Owner > Manager > Sotuvchi
"""

from rest_framework.permissions import BasePermission
from rest_framework.request import Request

from .models import WorkerRole


# ============================================================
# YORDAMCHI FUNKSIYA
# ============================================================

def _get_worker(request: Request):
    """
    So'rov yuborgan foydalanuvchining Worker obyektini qaytaradi.
    Agar Worker mavjud bo'lmasa — None qaytaradi.
    """
    return getattr(request.user, 'worker', None)


# ============================================================
# PERMISSION KLASSLARI
# ============================================================

class IsSuperAdmin(BasePermission):
    """
    Faqat Django superadmin (is_superuser=True) uchun ruxsat.
    Tizim miqyosidagi amallar uchun ishlatiladi.
    Misol: barcha do'konlarni ko'rish, tizim sozlamalari.
    """
    message = "Bu amal faqat superadmin uchun ruxsat etilgan."

    def has_permission(self, request: Request, view) -> bool:
        return bool(request.user and request.user.is_superuser)


class IsOwner(BasePermission):
    """
    Faqat 'owner' rolidagi hodim uchun ruxsat.
    Do'kon egasi o'z do'konini to'liq boshqarishi uchun.
    Misol: hodim qo'shish/o'chirish, sozlamalarni o'zgartirish.
    """
    message = "Bu amal faqat do'kon egasi uchun ruxsat etilgan."

    def has_permission(self, request: Request, view) -> bool:
        worker = _get_worker(request)
        return bool(worker and worker.role == WorkerRole.OWNER)


class IsManagerOrAbove(BasePermission):
    """
    'manager' yoki 'owner' rolidagi hodimlar uchun ruxsat.
    Boshqaruv amallari uchun ishlatiladi.
    Misol: hodimlar ro'yxatini ko'rish, xarajat qo'shish.
    """
    message = "Bu amal faqat menejer yoki egasi uchun ruxsat etilgan."

    ALLOWED_ROLES = {WorkerRole.OWNER, WorkerRole.MANAGER}

    def has_permission(self, request: Request, view) -> bool:
        worker = _get_worker(request)
        return bool(worker and worker.role in self.ALLOWED_ROLES)


class IsSotuvchiOrAbove(BasePermission):
    """
    Barcha rollar uchun ruxsat (owner, manager, sotuvchi).
    Asosan autentifikatsiya qilingan har qanday hodim uchun.
    """
    message = "Bu amal faqat tizim hodimi uchun ruxsat etilgan."

    def has_permission(self, request: Request, view) -> bool:
        worker = _get_worker(request)
        return bool(worker and worker.status == 'active')


class CanAccess(BasePermission):
    """
    Muayyan frontend bo'limiga kirish ruxsatini tekshiradi.

    Worker.has_permission(code) metodidan foydalanadi.
    Hodimning roli + individual extra_permissions hisobga olinadi.

    Ishlatilishi:
        # Mahsulotlar bo'limiga kirish
        permission_classes = [IsAuthenticated, CanAccess('mahsulotlar')]

        # Sozlamalar bo'limiga kirish
        permission_classes = [IsAuthenticated, CanAccess('sozlamalar')]
    """

    def __init__(self, section: str) -> None:
        """
        Args:
            section: Permission kodi (masalan: 'mahsulotlar', 'sotuv')
        """
        self.section = section
        self.message = f"'{section}' bo'limiga kirish ruxsati yo'q."

    def has_permission(self, request: Request, view) -> bool:
        worker = _get_worker(request)
        return bool(worker and worker.has_permission(self.section))
