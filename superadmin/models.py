import uuid

from django.contrib.auth import get_user_model
from django.db import models

from store.models import Store

User = get_user_model()


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


# ============================================================
# SUPPORT TICKETS
# ============================================================

class TicketStatus(models.TextChoices):
    OPEN        = 'open',        'Ochiq'
    IN_PROGRESS = 'in_progress', "Ko'rilmoqda"
    RESOLVED    = 'resolved',    'Hal qilindi'
    CLOSED      = 'closed',      'Yopildi'


class TicketPriority(models.TextChoices):
    LOW    = 'low',    'Past'
    MEDIUM = 'medium', "O'rta"
    HIGH   = 'high',   'Yuqori'
    URGENT = 'urgent', 'Shoshilinch'


class SupportTicket(models.Model):
    """Do'kon egasi superadminga muammo yuboradi."""
    store       = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='tickets')
    title       = models.CharField(max_length=200, verbose_name="Sarlavha")
    description = models.TextField(verbose_name="Batafsil tavsif")
    status      = models.CharField(
        max_length=15, choices=TicketStatus.choices,
        default=TicketStatus.OPEN, verbose_name="Holati"
    )
    priority    = models.CharField(
        max_length=10, choices=TicketPriority.choices,
        default=TicketPriority.MEDIUM, verbose_name="Ustuvorlik"
    )
    resolved_at = models.DateTimeField(null=True, blank=True, verbose_name="Hal qilingan vaqt")
    created_on  = models.DateTimeField(auto_now_add=True)
    updated_on  = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Support ticket'
        verbose_name_plural = 'Support ticketlar'
        ordering            = ['-created_on']

    def __str__(self):
        return f"[{self.get_priority_display()}] {self.title} — {self.store.name}"


class TicketReply(models.Model):
    """Ticket javoblari — ham do'kon, ham superadmin yozishi mumkin."""
    ticket     = models.ForeignKey(SupportTicket, on_delete=models.CASCADE, related_name='replies')
    author     = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='ticket_replies')
    message    = models.TextField(verbose_name="Xabar")
    is_admin   = models.BooleanField(default=False, verbose_name="Superadmindan")
    created_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Ticket javob'
        verbose_name_plural = 'Ticket javoblar'
        ordering            = ['created_on']

    def __str__(self):
        who = "Admin" if self.is_admin else self.ticket.store.name
        return f"{who} — {self.created_on.strftime('%d.%m.%Y %H:%M')}"


# ============================================================
# REFERRAL TIZIMI
# ============================================================

class ReferralStatus(models.TextChoices):
    PENDING   = 'pending',   'Kutilmoqda'
    CONFIRMED = 'confirmed', 'Tasdiqlandi'
    REWARDED  = 'rewarded',  'Bonus berildi'


class Referral(models.Model):
    """
    Do'kon A -> Do'kon B ni taklif qiladi.
    Do'kon B ro'yxatdan o'tganda Do'kon A ga bonus beriladi.
    """
    referrer_store  = models.ForeignKey(
        Store, on_delete=models.CASCADE,
        related_name='referrals_made',
        verbose_name="Taklif qilgan do'kon"
    )
    referred_store  = models.ForeignKey(
        Store, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='referral_received',
        verbose_name="Taklif qilingan do'kon"
    )
    referral_code   = models.CharField(
        max_length=20, unique=True,
        verbose_name="Referral kodi"
    )
    status          = models.CharField(
        max_length=15, choices=ReferralStatus.choices,
        default=ReferralStatus.PENDING, verbose_name="Holati"
    )
    reward_days     = models.PositiveIntegerField(
        default=30, verbose_name="Bonus kunlar soni"
    )
    confirmed_at    = models.DateTimeField(null=True, blank=True, verbose_name="Tasdiqlangan vaqt")
    rewarded_at     = models.DateTimeField(null=True, blank=True, verbose_name="Bonus berilgan vaqt")
    created_on      = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Referral'
        verbose_name_plural = 'Referrallar'
        ordering            = ['-created_on']

    def __str__(self):
        referred = self.referred_store.name if self.referred_store else "Hali foydalanilmagan"
        return f"{self.referrer_store.name} → {referred} [{self.get_status_display()}]"


class StoreReferralCode(models.Model):
    """Har bir do'konning doimiy referral kodi."""
    store = models.OneToOneField(
        Store, on_delete=models.CASCADE,
        related_name='referral_code_obj',
        verbose_name="Do'kon"
    )
    code       = models.CharField(max_length=20, unique=True, verbose_name="Referral kodi")
    created_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = "Do'kon referral kodi"
        verbose_name_plural = "Do'kon referral kodlari"

    def __str__(self):
        return f"{self.store.name}: {self.code}"

    @classmethod
    def get_or_create_for_store(cls, store):
        obj, created = cls.objects.get_or_create(
            store=store,
            defaults={'code': cls._generate_code(store)}
        )
        return obj

    @classmethod
    def _generate_code(cls, store):
        base = store.name[:4].upper().replace(' ', '')
        suffix = uuid.uuid4().hex[:4].upper()
        return f"{base}{suffix}"
