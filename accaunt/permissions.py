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

from .models import WorkerRole, WorkerStatus


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
        return bool(worker and worker.status == WorkerStatus.ACTIVE)


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


# ============================================================
# SUBSCRIPTION PERMISSION'LAR (B20)
# ============================================================

class SubscriptionRequired(BasePermission):
    """
    Tarif rejada muayyan funksiya mavjudligini tekshiradi.

    Ishlatish:
        permission_classes = [IsAuthenticated, SubscriptionRequired('has_export')]

    Tekshiruv:
        1. Subscription mavjudmi?
        2. Status active yoki trial?
        3. plan.{feature} = True?

    StoreSettings bilan birgalikda ishlatish:
        IKKALASI True bo'lsagina funksiya ochiladi.
    """
    def __init__(self, feature: str) -> None:
        self.feature = feature
        self.message = (
            "Sizning tarif rejangiz bu funksiyani qo'llab-quvvatlamaydi. "
            "Rejangizni yangilang."
        )

    def has_permission(self, request: Request, view) -> bool:
        worker = _get_worker(request)
        if not worker:
            return False
        from config.cache_utils import get_subscription
        sub = get_subscription(worker.store_id)
        if not sub or not sub.is_active:
            self.message = "Obuna muddati tugagan. To'lov qiling."
            return False
        return bool(getattr(sub.plan, self.feature, False))


class BranchLimitPermission(BasePermission):
    """
    Filial yaratishda limit tekshiruvi.
    Faqat 'create' actionida ishlaydi.
    """
    message = "Tarif rejangiz bu amalni bajarishga ruxsat bermaydi."

    def has_permission(self, request: Request, view) -> bool:
        if getattr(view, 'action', None) != 'create':
            return True
        return _check_limit(request, 'Branch', 'max_branches')


class WarehouseLimitPermission(BasePermission):
    """Ombor yaratishda limit tekshiruvi."""
    message = "Tarif rejangiz bu amalni bajarishga ruxsat bermaydi."

    def has_permission(self, request: Request, view) -> bool:
        if getattr(view, 'action', None) != 'create':
            return True
        return _check_limit(request, 'Warehouse', 'max_warehouses')


class WorkerLimitPermission(BasePermission):
    """Xodim yaratishda limit tekshiruvi."""
    message = "Tarif rejangiz bu amalni bajarishga ruxsat bermaydi."

    def has_permission(self, request: Request, view) -> bool:
        if getattr(view, 'action', None) != 'create':
            return True
        return _check_limit(request, 'Worker', 'max_workers')


class ProductLimitPermission(BasePermission):
    """Mahsulot yaratishda limit tekshiruvi."""
    message = "Tarif rejangiz bu amalni bajarishga ruxsat bermaydi."

    def has_permission(self, request: Request, view) -> bool:
        if getattr(view, 'action', None) != 'create':
            return True
        return _check_limit(request, 'Product', 'max_products')


def _check_limit(request: Request, model_name: str, limit_attr: str) -> bool:
    """
    Umumiy limit tekshiruv funksiyasi.
    max_* = 0 bo'lsa → cheksiz → True qaytaradi.
    """
    worker = _get_worker(request)
    if not worker:
        return False

    from config.cache_utils import get_subscription
    sub = get_subscription(worker.store_id)
    if not sub:
        return True   # Subscription yo'q — tekshirilmaydi

    max_count = getattr(sub.plan, limit_attr, 0)
    if max_count == 0:
        return True   # Cheksiz

    # Joriy soni
    from django.apps import apps
    model_map = {
        'Branch':    ('store',     'Branch',    {'store': worker.store, 'status': 'active'}),
        'Warehouse': ('warehouse', 'Warehouse', {'store': worker.store, 'status': 'active'}),
        'Worker':    ('accaunt',   'Worker',    {'store': worker.store, 'status': 'active'}),
        'Product':   ('warehouse', 'Product',   {'store': worker.store, 'status': 'active'}),
    }
    if model_name not in model_map:
        return True

    app_label, model_label, filters = model_map[model_name]
    Model   = apps.get_model(app_label, model_label)
    current = Model.objects.filter(**filters).count()

    if current >= max_count:
        # Permission ob'ektida message o'rnatish
        _check_limit._last_message = (
            f"Tarif rejangiz maksimal {max_count} ta "
            f"{model_name.lower()} ga ruxsat beradi. "
            f"Hozirda {current} ta mavjud."
        )
        return False
    return True


class ReadOnlyIfExpired(BasePermission):
    """
    Subscription expired bo'lsa — cheklangan kirish rejimi.

    Ruxsat etilgan operatsiyalar (expired holatda):
      ✅ Barcha GET so'rovlari
      ✅ Login / Logout / Token refresh
      ✅ PATCH /api/v1/shifts/{id}/close/  (smena yopish)
      ✅ GET   /api/v1/export/*            (hisobot yuklab olish)
      ✅ GET   /api/v1/subscription/*      (obunani ko'rish)

    Qolgan barcha POST/PATCH/PUT/DELETE → 403
    """
    message = (
        "Obuna muddati tugagan. Faqat ma'lumot ko'rish mumkin. "
        "To'lov qilish uchun /api/v1/subscription/ ga murojaat qiling."
    )

    # Bu yo'llar har doim ruxsat etiladi (expired bo'lsa ham)
    _ALWAYS_ALLOWED_PATHS = {
        '/api/v1/auth/login/',
        '/api/v1/auth/logout/',
        '/api/v1/auth/token/refresh/',
        '/api/v1/subscription/',
        '/api/v1/subscription/plans/',
        '/api/v1/subscription/invoices/',
    }

    def has_permission(self, request: Request, view) -> bool:
        worker = _get_worker(request)
        if not worker:
            return True   # Auth view'lar o'zi boshqaradi

        from config.cache_utils import get_subscription
        sub = get_subscription(worker.store_id)

        # Active yoki trial — to'siq yo'q
        if not sub or sub.is_active:
            return True

        # GET — har doim ruxsat
        if request.method == 'GET':
            return True

        path = request.path

        # Har doim ruxsat etilgan yo'llar
        if path in self._ALWAYS_ALLOWED_PATHS:
            return True

        # Smena yopish (PATCH .../close/)
        if request.method == 'PATCH' and path.endswith('/close/'):
            return True

        # Qolganlar — blok
        return False
