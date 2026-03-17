"""
============================================================
SUBSCRIPTION — Modellar
============================================================
Modellar:
  PlanType              — Tarif reja turlari (TextChoices)
  SubscriptionStatus    — Obuna holatlari (TextChoices)
  SubscriptionPlan      — Tarif rejalari (admin boshqaradi)
  Subscription          — Har bir do'konning joriy obunasi (OneToOne → Store)
  SubscriptionInvoice   — To'lov tarixi (immutable)
  SubscriptionDowngradeLog — LIFO: qaysi ob'ektlar inactive qilindi

Qoidalar:
  1. Har bir Store ga bitta Subscription (OneToOne)
  2. Store yaratilganda → Trial avtomatik (signal orqali)
  3. Trial = eng qulay reja, 30 kun (settings.SUBSCRIPTION_TRIAL_DAYS)
  4. Downgrade → LIFO inactive (newest first), previous_status saqlanadi
  5. Upgrade → faqat previous_status='active' ob'ektlar qaytariladi
  6. Hech qanday ma'lumot o'chirilmaydi — faqat status o'zgaradi
"""

from django.db import models


# ============================================================
# CHOICES
# ============================================================

class PlanType(models.TextChoices):
    TRIAL      = 'trial',      'Sinov (30 kun)'
    BASIC      = 'basic',      'Asosiy'
    PRO        = 'pro',        'Professional'
    ENTERPRISE = 'enterprise', 'Korporativ'


class SubscriptionStatus(models.TextChoices):
    TRIAL     = 'trial',     'Sinov davri'
    ACTIVE    = 'active',    'Faol'
    EXPIRED   = 'expired',   'Muddati tugagan'
    CANCELLED = 'cancelled', 'Bekor qilingan'


# ============================================================
# TARIF REJA
# ============================================================

class SubscriptionPlan(models.Model):
    """
    Tarif rejalari — faqat superadmin yaratadi va boshqaradi.

    max_* = 0 → cheksiz (Enterprise uchun).
    has_* = False → bu funksiya ushbu rejada yo'q.

    StoreSettings bilan munosabat:
      StoreSettings.kpi_enabled  → do'kon o'zi yoq/yopdi
      SubscriptionPlan.has_kpi   → tarif rejada mavjudmi
      IKKALASI True bo'lsagina funksiya ishlaydi.
    """
    plan_type    = models.CharField(
        max_length=20,
        choices=PlanType.choices,
        unique=True,
        verbose_name="Reja turi",
    )
    name         = models.CharField(
        max_length=100,
        verbose_name="Nomi",
    )
    description  = models.TextField(
        blank=True,
        verbose_name="Tavsif",
    )

    # ---- Narx (UZS) ----
    price_monthly  = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name="Oylik narx (UZS)",
    )
    price_yearly   = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name="Yillik narx (UZS)",
    )
    yearly_discount = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        verbose_name="Yillik chegirma (%)",
    )

    # ---- Cheklovlar (0 = cheksiz) ----
    max_branches   = models.PositiveIntegerField(default=1,   verbose_name="Maks. filiallar")
    max_warehouses = models.PositiveIntegerField(default=1,   verbose_name="Maks. omborlar")
    max_workers    = models.PositiveIntegerField(default=3,   verbose_name="Maks. xodimlar")
    max_products   = models.PositiveIntegerField(default=100, verbose_name="Maks. mahsulotlar")

    # ---- Funksiya flaglari ----
    # StoreSettings dagi har bir modul uchun mos flag

    # Asosiy modullar
    has_subcategory    = models.BooleanField(default=False, verbose_name="Subkategoriyalar")
    has_sale_return    = models.BooleanField(default=False, verbose_name="Qaytarishlar")
    has_wastage        = models.BooleanField(default=False, verbose_name="Isrof yozuvlari")
    has_stock_audit    = models.BooleanField(default=False, verbose_name="Inventarizatsiya")
    has_kpi            = models.BooleanField(default=False, verbose_name="KPI moduli")
    has_multi_currency = models.BooleanField(default=False, verbose_name="Ko'p valyuta")
    has_supplier       = models.BooleanField(default=False, verbose_name="Yetkazib beruvchi")

    # Kengaytirilgan modullar
    has_export         = models.BooleanField(default=False, verbose_name="Export (Excel/PDF)")
    has_dashboard      = models.BooleanField(default=False, verbose_name="Dashboard")
    has_qr_bulk        = models.BooleanField(default=False, verbose_name="Bulk QR kod")
    has_audit_log      = models.BooleanField(default=False, verbose_name="Audit log")

    # V2 modullar
    has_telegram       = models.BooleanField(default=False, verbose_name="Telegram bot (v2)")

    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Tarif reja'
        verbose_name_plural = 'Tarif rejalar'
        ordering            = ['price_monthly']

    def __str__(self) -> str:
        return f"{self.name} ({self.get_plan_type_display()})"

    def is_unlimited(self, attr: str) -> bool:
        """max_branches, max_workers ... = 0 bo'lsa cheksiz."""
        return getattr(self, attr, 1) == 0


# ============================================================
# OBUNA
# ============================================================

class Subscription(models.Model):
    """
    Har bir do'konning joriy obunasi.

    Yaratilishi:
      Store yaratilganda → signal → Trial avtomatik yaratiladi.

    Holatlari:
      trial    → sinov davri (30 kun)
      active   → to'lov qilingan, faol
      expired  → muddati tugagan → read-only rejim
      cancelled→ egasi tomonidan bekor qilingan → read-only

    Ogohlantirish:
      notified_10d/3d/1d → Celery task bir marta bajaradi,
      flag True bo'lgandan keyin qaytarilmaydi.
      To'lov qilinganda flaglar avtomatik reset qilinadi.
    """
    store  = models.OneToOneField(
        'store.Store',
        on_delete=models.CASCADE,
        related_name='subscription',
        verbose_name="Do'kon",
    )
    plan   = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT,
        related_name='subscriptions',
        verbose_name="Tarif reja",
    )
    status = models.CharField(
        max_length=15,
        choices=SubscriptionStatus.choices,
        default=SubscriptionStatus.TRIAL,
        verbose_name="Holati",
    )
    is_yearly = models.BooleanField(
        default=False,
        verbose_name="Yillik to'lov",
    )

    # ---- Sana ----
    start_date = models.DateField(verbose_name="Boshlanish sanasi")
    end_date   = models.DateField(verbose_name="Tugash sanasi")

    # ---- To'lov ----
    last_payment_date   = models.DateField(
        null=True, blank=True,
        verbose_name="Oxirgi to'lov sanasi",
    )
    last_payment_amount = models.DecimalField(
        max_digits=15, decimal_places=2,
        null=True, blank=True,
        verbose_name="Oxirgi to'lov summasi (UZS)",
    )

    # ---- Ogohlantirish flaglari ----
    # True = yuborildi, qaytarilmaydi
    notified_10d = models.BooleanField(default=False, verbose_name="10 kun ogohlantirish")
    notified_3d  = models.BooleanField(default=False, verbose_name="3 kun ogohlantirish")
    notified_1d  = models.BooleanField(default=False, verbose_name="1 kun ogohlantirish")

    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Obuna'
        verbose_name_plural = 'Obunalar'

    def __str__(self) -> str:
        return f"{self.store.name} — {self.plan.name} ({self.get_status_display()})"

    @property
    def days_left(self) -> int:
        """Necha kun qoldi."""
        from datetime import date
        delta = (self.end_date - date.today()).days
        return max(0, delta)

    @property
    def is_active(self) -> bool:
        """Faol yoki trial bo'lsa True."""
        return self.status in (SubscriptionStatus.TRIAL, SubscriptionStatus.ACTIVE)

    def reset_notification_flags(self):
        """To'lov qilinganda ogohlantirish flaglarini tozalash."""
        self.notified_10d = False
        self.notified_3d  = False
        self.notified_1d  = False


# ============================================================
# TO'LOV TARIXI
# ============================================================

class SubscriptionInvoice(models.Model):
    """
    To'lov yozuvi — immutable (o'zgartirilmaydi va o'chirilmaydi).

    Faqat superadmin qo'shadi.
    To'lov qo'shilganda Subscription.end_date avtomatik uzaytiriladi.
    """
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE,
        related_name='invoices',
        verbose_name="Obuna",
    )
    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT,
        verbose_name="Tarif reja (to'lov vaqtida)",
    )
    amount      = models.DecimalField(
        max_digits=15, decimal_places=2,
        verbose_name="To'lov summasi (UZS)",
    )
    is_yearly   = models.BooleanField(
        default=False,
        verbose_name="Yillik to'lov",
    )
    period_from = models.DateField(verbose_name="Davr boshi")
    period_to   = models.DateField(verbose_name="Davr oxiri")
    note        = models.TextField(blank=True, verbose_name="Izoh")
    created_by  = models.ForeignKey(
        'accaunt.Worker',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name="Qo'shgan admin",
    )
    paid_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Qo'shilgan vaqt",
    )

    class Meta:
        verbose_name        = "To'lov"
        verbose_name_plural = "To'lovlar"
        ordering            = ['-paid_at']

    def __str__(self) -> str:
        return (
            f"{self.subscription.store.name} — "
            f"{self.amount:,.0f} UZS ({self.period_from} → {self.period_to})"
        )


# ============================================================
# DOWNGRADE LOG
# ============================================================

class SubscriptionDowngradeLog(models.Model):
    """
    Downgrade yoki expiry paytida tizim tomonidan inactive qilingan
    ob'ektlar ro'yxati.

    Maqsad:
      Upgrade bo'lganda AYNAN SHU ob'ektlarni qaytarish.
      previous_status='active' bo'lganlar qaytariladi.
      (Admin o'zi inactive qilgan ob'ektlar qaytarilmaydi.)

    LIFO tartibi:
      Eng yangi ob'ektlar birinchi inactive qilinadi (created_on desc).
      Reactivate: eng eski birinchi (deactivated_at asc).
    """
    subscription    = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE,
        related_name='downgrade_logs',
        verbose_name="Obuna",
    )
    object_type     = models.CharField(
        max_length=20,
        verbose_name="Ob'ekt turi",
        # 'Branch' | 'Warehouse' | 'Worker'
    )
    object_id       = models.PositiveIntegerField(
        verbose_name="Ob'ekt ID",
    )
    previous_status = models.CharField(
        max_length=10,
        verbose_name="Oldingi holati",
        # 'active' → tizim inactive qilgan
        # 'inactive' → allaqachon inactive edi (bu holat bo'lmasligi kerak)
    )
    deactivated_at  = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Inactive qilingan vaqt",
    )
    reactivated_at  = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Qayta faollashtirilgan vaqt",
    )
    note            = models.TextField(
        blank=True,
        verbose_name="Izoh",
    )

    class Meta:
        verbose_name        = 'Downgrade log'
        verbose_name_plural = 'Downgrade loglar'
        ordering            = ['deactivated_at']

    def __str__(self) -> str:
        return (
            f"{self.object_type} #{self.object_id} — "
            f"{self.subscription.store.name}"
        )
