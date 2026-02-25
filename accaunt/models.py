"""
============================================================
ACCAUNT APP — Modellar
============================================================
Modellar:
  CustomUser   — Kengaytirilgan foydalanuvchi modeli
  UserManager  — CustomUser uchun manager
  WorkerRole   — Sobit hodim rollari (TextChoices)
  Worker       — Do'kon hodimi
  AuditLog     — Tizim amallari jurnali

Ruxsat tizimi:
  - Rollar sobit: owner, manager, seller
  - Har bir permission = frontendda bitta bo'lim (sahifa)
  - ROLE_PERMISSIONS — har bir rolning standart permission ro'yxati
  - Worker.permissions — hodimning haqiqiy ruxsatlar ro'yxati (to'g'ridan-to'g'ri JSONField)
"""

from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import RegexValidator


# ============================================================
# VALIDATORLAR
# ============================================================

phone_regex = RegexValidator(
    regex=r'^\+998\d{9}$',
    message="Telefon raqami '+998901234567' formatida bo'lishi kerak."
)


# ============================================================
# HODIM ROLLARI (Sobit — DB da saqlanmaydi)
# ============================================================

class WorkerRole(models.TextChoices):
    """
    Do'kon hodimlarining rollari.
    Har bir rol o'ziga xos permission to'plamiga ega.
    Rollar sobit — kod ichida belgilangan, DB dan o'zgartirib bo'lmaydi.
    """
    OWNER   = 'owner',   'Ega'
    MANAGER = 'manager', 'Menejer'
    SELLER  = 'seller',  'Sotuvchi'


# ============================================================
# PERMISSION KODLARI (Frontendning bo'limlari)
# ============================================================

# Tizimda mavjud barcha permission kodlar.
# Har bir kod = frontendda bitta bo'lim (sahifa).
# O'sha bo'limga kirish ruxsati bor bo'lsa — bo'lim to'liq ochiladi.
ALL_PERMISSIONS: list[str] = [
    'boshqaruv',   # Boshqaruv paneli (Dashboard)
    'sotuv',       # Sotuv oynasi (POS — kassa)
    'dokonlar',    # Do'konlar va filiallar
    'ombor',       # Ombor (sklad)
    'mahsulotlar', # Mahsulotlar katalogi
    'xodimlar',    # Xodimlarni boshqarish
    'savdolar',    # Savdolar tarixi va hisobotlar
    'xarajatlar',  # Xarajatlarni boshqarish
    'mijozlar',    # Mijozlar bazasi
    'sozlamalar',  # Do'kon sozlamalari
]


# ============================================================
# ROLLAR VA ULARNING STANDART PERMISSION'LARI
# ============================================================

# Har bir rolning standart permission kodlari.
# Individual worker uchun extra_permissions orqali qo'shish/olib tashlash mumkin.
ROLE_PERMISSIONS: dict[str, list[str]] = {

    # Ega — barcha bo'limlarga kirish huquqi bor
    WorkerRole.OWNER: [
        'boshqaruv', 'sotuv', 'dokonlar', 'ombor',
        'mahsulotlar', 'xodimlar', 'savdolar',
        'xarajatlar', 'mijozlar', 'sozlamalar',
    ],

    # Menejer — sozlamalardan tashqari hamma bo'lim
    WorkerRole.MANAGER: [
        'boshqaruv', 'sotuv', 'dokonlar', 'ombor',
        'mahsulotlar', 'xodimlar', 'savdolar',
        'xarajatlar', 'mijozlar',
        # 'sozlamalar' yo'q — faqat ega sozlamalarni boshqaradi
    ],

    # Sotuvchi — faqat savdo va mahsulot bo'limlari
    WorkerRole.SELLER: [
        'sotuv', 'savdolar', 'mijozlar',
        'ombor', 'mahsulotlar',
    ],
}


# ============================================================
# HODIM HOLATLARI
# ============================================================

class WorkerStatus(models.TextChoices):
    """Hodim faollik holatlari"""
    ACTIVE        = 'active',        'Faol'
    TATIL         = 'tatil',         'Tatilda'
    ISHDAN_KETGAN = 'ishdan_ketgan', 'Ishdan ketgan'


# ============================================================
# USER MANAGER
# ============================================================

class UserManager(BaseUserManager):
    """
    CustomUser uchun maxsus manager.
    create_user() va create_superuser() metodlarini qayta yozadi.
    """

    def create_user(
        self,
        username: str,
        email: str,
        phone1: str,
        password: str = None,
        first_name: str = '',
        last_name: str = '',
        is_superuser: bool = False,
        is_staff: bool = False,
        phone2: str = None,
    ) -> 'CustomUser':
        """Oddiy foydalanuvchi yaratish."""
        if not username:
            raise ValueError("Foydalanuvchi 'username' bo'lishi shart!")

        user = self.model(
            first_name=first_name,
            last_name=last_name,
            email=self.normalize_email(email),
            username=username,
            is_superuser=is_superuser,
            is_staff=is_staff,
            phone1=phone1,
            phone2=phone2,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(
        self,
        email: str,
        username: str,
        password: str = None,
    ) -> 'CustomUser':
        """Superadmin yaratish — barcha ruxsatlar avtomatik beriladi."""
        user = self.create_user(
            password=password,
            first_name='Super',
            last_name='Admin',
            email=email,
            username=username,
            is_superuser=True,
            is_staff=True,
            phone1='+998990000000',
        )
        user.save(using=self._db)
        return user


# ============================================================
# CUSTOM USER
# ============================================================

class CustomUser(AbstractUser):
    """
    Kengaytirilgan foydalanuvchi modeli.

    Qo'shimcha maydonlar:
      phone1    — Asosiy telefon raqam (majburiy)
      phone2    — Qo'shimcha telefon raqam (ixtiyoriy)
      status    — Faollik holati (True = faol, False = bloklangan)
      created_on — Ro'yxatga olingan vaqt
    """

    phone1 = models.CharField(
        validators=[phone_regex],
        max_length=13,
        verbose_name="Asosiy telefon"
    )
    phone2 = models.CharField(
        validators=[phone_regex],
        max_length=13,
        null=True,
        blank=True,
        verbose_name="Qo'shimcha telefon"
    )
    status = models.BooleanField(
        default=True,
        verbose_name="Holati",
        help_text="False bo'lsa, foydalanuvchi tizimga kira olmaydi"
    )
    created_on = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Ro'yxatdan o'tgan vaqti"
    )

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    objects = UserManager()

    class Meta:
        verbose_name = 'Foydalanuvchi'
        verbose_name_plural = 'Foydalanuvchilar'

    def __str__(self) -> str:
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name or self.username


# ============================================================
# WORKER (Hodim)
# ============================================================

class Worker(models.Model):
    """
    Do'kon hodimi.

    Har bir hodim:
      - Bitta CustomUser bilan bog'liq (OneToOne)
      - Sobit rollardan biriga ega: owner, manager, seller
      - Do'kon va filialga biriktiriladi
      - permissions — hodimning haqiqiy ruxsatlar ro'yxati (to'g'ridan-to'g'ri saqlanadi)

    Permission tizimi:
      Hodim yaratilganda ROLE_PERMISSIONS[role] dan avtomatik to'ldiriladi.
      Keyinchalik PATCH /workers/{id}/ orqali istalgan ro'yxat bilan almashtiriladi.

    Misol:
      {"permissions": ["sotuv", "ombor", "mahsulotlar", "xarajatlar"]}
    """

    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='worker',
        verbose_name="Foydalanuvchi"
    )
    role = models.CharField(
        max_length=20,
        choices=WorkerRole.choices,
        default=WorkerRole.SELLER,
        verbose_name="Roli"
    )
    store = models.ForeignKey(
        'store.Store',
        on_delete=models.CASCADE,
        related_name='workers',
        null=True,
        blank=True,
        verbose_name="Do'koni"
    )
    branch = models.ForeignKey(
        'store.Branch',
        on_delete=models.SET_NULL,
        related_name='workers',
        null=True,
        blank=True,
        verbose_name="Filiali"
    )
    salary = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Maoshi (UZS)"
    )
    status = models.CharField(
        max_length=15,
        choices=WorkerStatus.choices,
        default=WorkerStatus.ACTIVE,
        verbose_name="Holati"
    )

    # Hodimning haqiqiy ruxsatlar ro'yxati.
    # Hodim yaratilganda ROLE_PERMISSIONS[role] dan avtomatik to'ldiriladi.
    # Owner PATCH /workers/{id}/ orqali istalgan ro'yxat bilan almashtiria oladi.
    # Misol: ["sotuv", "ombor", "mahsulotlar"]
    permissions = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Ruxsatlar",
        help_text="Hodim kira oladigan bo'lim kodlari ro'yxati"
    )

    created_on = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Qo'shilgan vaqti"
    )

    class Meta:
        verbose_name = 'Hodim'
        verbose_name_plural = 'Hodimlar'

    def __str__(self) -> str:
        return f"{self.user} ({self.get_role_display()})"

    def get_permissions(self) -> list[str]:
        """
        Hodimning ruxsatlar ro'yxatini qaytaradi (alifbo tartibida).

        Returns:
            Hodim kira oladigan bo'limlar ro'yxati (masalan: ['mahsulotlar', 'sotuv'])
        """
        return sorted(self.permissions or [])

    def has_permission(self, code: str) -> bool:
        """
        Hodimda berilgan bo'limga kirish ruxsati borligini tekshiradi.

        Args:
            code: Permission kodi (masalan: 'mahsulotlar', 'sotuv')
        Returns:
            True — ruxsat mavjud, False — mavjud emas
        """
        return code in (self.permissions or [])


# ============================================================
# AUDIT LOG (Tizim amallari jurnali)
# ============================================================

class AuditLog(models.Model):
    """
    Tizimda amalga oshirilgan muhim amallar jurnali.

    Har qanday muhim amal (yaratish, o'chirish, tizimga kirish va h.k.)
    bu modelda qayd etiladi. Xavfsizlik auditi va monitoring uchun kerak.
    """

    class Action(models.TextChoices):
        """Tizimda bajarilishi mumkin bo'lgan amal turlari"""
        CREATE = 'create', 'Yaratdi'
        UPDATE = 'update', 'Yangiladi'
        DELETE = 'delete', "O'chirdi"
        LOGIN  = 'login',  'Tizimga kirdi'
        LOGOUT = 'logout', 'Tizimdan chiqdi'
        ASSIGN = 'assign', "Tayinladi"

    # Kim amal bajardi (o'chirilsa NULL qoladi — log yo'qolmaydi)
    actor = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        verbose_name="Amal bajaruvchi"
    )
    action = models.CharField(
        max_length=20,
        choices=Action.choices,
        verbose_name="Amal turi"
    )
    # Qaysi model ustida amal bajarildi (masalan: 'Worker', 'Trade')
    target_model = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Model nomi"
    )
    target_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Ob'ekt ID"
    )
    description = models.TextField(
        blank=True,
        verbose_name="Tavsifi"
    )
    # Qo'shimcha ma'lumotlar: eski/yangi qiymatlar, IP manzil va h.k.
    extra_data = models.JSONField(
        null=True,
        blank=True,
        verbose_name="Qo'shimcha ma'lumotlar"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Vaqti"
    )

    class Meta:
        verbose_name = 'Audit log'
        verbose_name_plural = 'Audit loglar'
        ordering = ['-created_at']

    def __str__(self) -> str:
        actor_name = str(self.actor) if self.actor else "Tizim"
        return f"{actor_name} | {self.get_action_display()} | {self.target_model} #{self.target_id}"
