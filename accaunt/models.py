"""
============================================================
ACCAUNT APP — Modellar
============================================================
Bu fayl tizimning barcha foydalanuvchi va ruxsat modellarini
o'z ichiga oladi:

  CustomUser  — Kengaytirilgan foydalanuvchi modeli
  UserManager — CustomUser uchun manager
  Permission  — Frontend/backend ruxsatlar
  Role        — Hodim rollari
  Worker      — Do'kon hodimi
  AuditLog    — Tizim amallari jurnali
"""

from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import RegexValidator


# ============================================================
# VALIDATORLAR
# ============================================================

# O'zbekiston telefon raqami formati: +998901234567
phone_regex = RegexValidator(
    regex=r'^\+998\d{9}$',
    message="Telefon raqami '+998901234567' formatida bo'lishi kerak."
)


# ============================================================
# KONSTANTLAR
# ============================================================

class WorkerStatus(models.TextChoices):
    """Hodim faollik holatlari"""
    ACTIVE = 'active', 'Faol'
    DEACTIVE = 'deactive', 'Faol emas'


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
        """
        Oddiy foydalanuvchi yaratish.
        username va phone1 majburiy maydonlar.
        """
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
        """
        Superadmin yaratish.
        Barcha ruxsatlar avtomatik beriladi.
        """
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

    Django standart User modeliga qo'shimcha maydonlar:
      phone1    — Asosiy telefon raqam (majburiy)
      phone2    — Qo'shimcha telefon raqam (ixtiyoriy)
      status    — Faollik holati (True = faol)
      created_on — Ro'yxatga olingan sana
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
# PERMISSION (Ruxsat)
# ============================================================

class Permission(models.Model):
    """
    Tizim ruxsatlari.
    Frontend va backend uchun alohida ruxsat kodlari.

    Misol:
      name="Mahsulot qo'shish", code="product.add"
      name="Hisobotni ko'rish", code="report.view"
    """

    name = models.CharField(
        max_length=100,
        verbose_name="Nomi"
    )
    code = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Kodi",
        help_text="Masalan: product.add, report.view, trade.create"
    )
    description = models.TextField(
        blank=True,
        verbose_name="Tavsifi"
    )

    class Meta:
        verbose_name = 'Ruxsat'
        verbose_name_plural = 'Ruxsatlar'
        ordering = ['code']

    def __str__(self) -> str:
        return self.code


# ============================================================
# ROLE (Rol)
# ============================================================

class Role(models.Model):
    """
    Hodim rollari.
    Har bir rol bir nechta ruxsatlarni o'z ichiga oladi.

    Standart rollar:
      owner   — Do'kon egasi (barcha huquqlar)
      manager — Menejer (boshqaruv huquqlari)
      cashier — Kassir (savdo huquqlari)
      viewer  — Kuzatuvchi (faqat ko'rish)
    """

    name = models.CharField(
        max_length=100,
        verbose_name="Nomi"
    )
    code = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Kodi",
        help_text="Masalan: owner, manager, cashier, viewer"
    )
    permissions = models.ManyToManyField(
        Permission,
        related_name='roles',
        blank=True,
        verbose_name="Ruxsatlar"
    )

    class Meta:
        verbose_name = 'Rol'
        verbose_name_plural = 'Rollar'

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"


# ============================================================
# WORKER (Hodim)
# ============================================================

class Worker(models.Model):
    """
    Do'kon hodimi.

    Har bir hodim:
      - Bitta CustomUser bilan bog'liq (OneToOne)
      - Bitta rolga ega (FK → Role)
      - Qo'shimcha individual ruxsatlarga ega bo'lishi mumkin
      - Bitta do'kon va filialga biriktiriladi

    Do'kon egasi ham Worker hisoblanadi — 'owner' roli bilan.
    """

    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='worker',
        verbose_name="Foydalanuvchi"
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='workers',
        verbose_name="Roli"
    )
    # Rol ruxsatlaridan tashqari qo'shimcha individual ruxsatlar
    extra_permissions = models.ManyToManyField(
        Permission,
        blank=True,
        related_name='workers',
        verbose_name="Qo'shimcha ruxsatlar"
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
        verbose_name="Filioli"
    )
    salary = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Maoshi (UZS)"
    )
    status = models.CharField(
        max_length=10,
        choices=WorkerStatus.choices,
        default=WorkerStatus.ACTIVE,
        verbose_name="Holati"
    )
    created_on = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Qo'shilgan vaqti"
    )

    class Meta:
        verbose_name = 'Hodim'
        verbose_name_plural = 'Hodimlar'

    def __str__(self) -> str:
        return f"{self.user} — {self.role}"

    def get_permissions(self) -> set:
        """
        Hodimning barcha ruxsatlarini qaytaradi.
        Rol ruxsatlari + qo'shimcha individual ruxsatlar birlashtirilib
        Set sifatida qaytariladi (takrorlar yo'q).
        """
        role_permissions = self.role.permissions.all() if self.role else Permission.objects.none()
        extra_permissions = self.extra_permissions.all()
        return set(role_permissions) | set(extra_permissions)

    def has_permission(self, code: str) -> bool:
        """
        Hodimda berilgan ruxsat mavjudligini tekshiradi.

        Args:
            code: Ruxsat kodi (masalan: 'product.add', 'report.view')
        Returns:
            True — ruxsat mavjud, False — yo'q
        """
        return any(p.code == code for p in self.get_permissions())


# ============================================================
# AUDIT LOG (Tizim amallari jurnali)
# ============================================================

class AuditLog(models.Model):
    """
    Tizimda amalga oshirilgan muhim amallar jurnali.

    Har qanday muhim amal (yaratish, o'chirish, tizimga kirish va h.k.)
    bu modelda qayd etiladi. Xavfsizlik auditi va monitoring uchun kerak.

    Misol:
      Kim: Ahmadov Alisher
      Nima qildi: Mahsulot yaratdi
      Qaysi ob'ektga: Product #42
      Qachon: 2026-02-18 10:30:00
    """

    class Action(models.TextChoices):
        """Tizimda bajarilishi mumkin bo'lgan amal turlari"""
        CREATE = 'create', 'Yaratdi'
        UPDATE = 'update', 'Yangiladi'
        DELETE = 'delete', "O'chirdi"
        LOGIN = 'login', 'Tizimga kirdi'
        LOGOUT = 'logout', 'Tizimdan chiqdi'
        ASSIGN = 'assign', "Tayinladi"

    # Kim amal bajardi (foydalanuvchi o'chirilsa, NULL qoladi — log saqlanadi)
    actor = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        verbose_name="Amal bajaruvchi"
    )
    # Qanday amal bajarildi
    action = models.CharField(
        max_length=20,
        choices=Action.choices,
        verbose_name="Amal turi"
    )
    # Qaysi model ustida amal bajarildi (masalan: 'Product', 'Trade')
    target_model = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Model nomi"
    )
    # O'sha modelning ID si
    target_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Ob'ekt ID"
    )
    # Qisqacha tavsif (masalan: "iPhone 15 Pro qo'shildi")
    description = models.TextField(
        blank=True,
        verbose_name="Tavsifi"
    )
    # Qo'shimcha ma'lumotlar JSON formatida (eski/yangi qiymatlar va h.k.)
    extra_data = models.JSONField(
        null=True,
        blank=True,
        verbose_name="Qo'shimcha ma'lumotlar"
    )
    # Amal bajarilgan vaqt
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Vaqti"
    )

    class Meta:
        verbose_name = 'Audit log'
        verbose_name_plural = 'Audit loglar'
        ordering = ['-created_at']  # Eng yangi log birinchi ko'rsatiladi

    def __str__(self) -> str:
        actor_name = str(self.actor) if self.actor else "Tizim"
        return f"{actor_name} | {self.get_action_display()} | {self.target_model} #{self.target_id}"
