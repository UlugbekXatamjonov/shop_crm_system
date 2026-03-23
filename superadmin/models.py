from django.db import models
from store.models import Store


# ============================================================
# KUPON TIZIMI
# ============================================================

class CouponType(models.TextChoices):
    FREE_DAYS   = 'free_days',   'Bepul kunlar'
    PERCENT_OFF = 'percent_off', 'Foiz chegirma'
    AMOUNT_OFF  = 'amount_off',  'Summa chegirma'


class Coupon(models.Model):
    """
    Superadmin tomonidan yaratiladigan kuponlar.
    Do'kon egasi kupon kodi kiritib obunasiga qo'llaydi.
    """
    code         = models.CharField(max_length=50, unique=True, verbose_name="Kupon kodi")
    type         = models.CharField(max_length=20, choices=CouponType.choices, verbose_name="Tur")
    value        = models.DecimalField(
        max_digits=10, decimal_places=2,
        verbose_name="Qiymat (kun / % / so'm)"
    )
    max_uses     = models.PositiveIntegerField(
        null=True, blank=True,
        verbose_name="Maksimal foydalanish (null=cheksiz)"
    )
    used_count   = models.PositiveIntegerField(default=0, verbose_name="Ishlatilgan marta")
    valid_from   = models.DateTimeField(verbose_name="Boshlanish sanasi")
    valid_to     = models.DateTimeField(verbose_name="Tugash sanasi")
    for_new_only = models.BooleanField(default=False, verbose_name="Faqat yangi do'konlar uchun")
    plan         = models.ForeignKey(
        'subscription.SubscriptionPlan',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='coupons',
        verbose_name="Faqat ushbu tarif uchun (null=hammaga)"
    )
    is_active    = models.BooleanField(default=True, verbose_name="Faolmi")
    description  = models.TextField(blank=True, verbose_name="Izoh")
    created_on   = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Kupon'
        verbose_name_plural = 'Kuponlar'
        ordering            = ['-created_on']

    def __str__(self):
        return f"{self.code} ({self.get_type_display()}: {self.value})"

    @property
    def is_exhausted(self):
        """Maksimal foydalanish limitiga yetdimi?"""
        if self.max_uses is None:
            return False
        return self.used_count >= self.max_uses

    def can_be_used_by(self, store):
        """Bu do'kon bu kuponni ishlatishi mumkinmi?"""
        from django.utils import timezone
        now = timezone.now()
        if not self.is_active:
            return False, "Kupon faol emas."
        if now < self.valid_from:
            return False, "Kupon hali amal qilmaydi."
        if now > self.valid_to:
            return False, "Kupon muddati tugagan."
        if self.is_exhausted:
            return False, "Kupon limiti tugagan."
        if self.for_new_only:
            has_paid = store.subscription_set.filter(status='active').exists()
            if has_paid:
                return False, "Kupon faqat yangi do'konlar uchun."
        if CouponUsage.objects.filter(coupon=self, store=store).exists():
            return False, "Siz bu kuponni allaqachon ishlatgansiz."
        return True, None


class CouponUsage(models.Model):
    """Kim qaysi kuponni qachon ishlatganini saqlaydi."""
    coupon         = models.ForeignKey(Coupon, on_delete=models.CASCADE, related_name='usages')
    store          = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='coupon_usages')
    applied_at     = models.DateTimeField(auto_now_add=True)
    discount_value = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name="Berilgan chegirma qiymati"
    )
    note           = models.TextField(blank=True, verbose_name="Izoh")

    class Meta:
        verbose_name        = 'Kupon foydalanish'
        verbose_name_plural = 'Kupon foydalanishlar'
        unique_together     = ('coupon', 'store')
        ordering            = ['-applied_at']

    def __str__(self):
        return f"{self.store} — {self.coupon.code} ({self.applied_at.date()})"


# ============================================================
# ADMIN O'ZINING XARAJATLARI
# ============================================================

class AdminExpenseCategory(models.TextChoices):
    SERVER    = 'server',    'Server / Hosting'
    SMS       = 'sms',       'SMS xizmat'
    DOMAIN    = 'domain',    'Domain / SSL'
    MARKETING = 'marketing', 'Marketing'
    SALARY    = 'salary',    'Maosh'
    OTHER     = 'other',     'Boshqa'


class AdminExpense(models.Model):
    """
    Loyiha egasining (superadmin) xarajatlari.
    Moliyaviy dashboard da sof foyda hisoblash uchun ishlatiladi.
    """
    title      = models.CharField(max_length=200, verbose_name="Nomi")
    category   = models.CharField(
        max_length=20,
        choices=AdminExpenseCategory.choices,
        default=AdminExpenseCategory.OTHER,
        verbose_name="Kategoriya"
    )
    amount     = models.DecimalField(
        max_digits=14, decimal_places=2,
        verbose_name="Summa (UZS)"
    )
    date       = models.DateField(verbose_name="Sana")
    note       = models.TextField(blank=True, verbose_name="Izoh")
    created_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Admin xarajati'
        verbose_name_plural = 'Admin xarajatlari'
        ordering            = ['-date']

    def __str__(self):
        return f"{self.title} — {self.amount:,.0f} so'm ({self.date})"
