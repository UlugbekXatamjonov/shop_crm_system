"""
============================================================
TRADE APP — Modellar
============================================================
Modellar:
  CustomerStatus    — Mijoz holati (TextChoices): active | inactive
  PaymentType       — To'lov turi (TextChoices): cash | card | mixed | debt
  SaleStatus        — Sotuv holati (TextChoices): completed | cancelled
  SaleReturnStatus  — Qaytarish holati (TextChoices): pending | confirmed | cancelled
  CustomerGroup     — Mijoz guruhi (chegirma % bilan)
  Customer          — Mijoz (nasiya qoldig'i, guruh, do'kon)
  Sale              — Sotuv (savdo yozuvi, atomic transaction bilan yaratiladi)
  SaleItem          — Sotuv elementi (mahsulot, miqdor, narx)
  SaleReturn        — Qaytarish (BOSQICH 5, confirmed → StockMovement(IN) avtomatik)
  SaleReturnItem    — Qaytarish elementi (mahsulot, miqdor, narx)

Multi-tenant: barcha modellar store(FK) orqali ajratilgan.

Bog'liqliklar:
  Sale.smena(FK → store.Smena)          — BOSQICH 3
  SaleItem.product(FK → warehouse.Product) — BOSQICH 1
  Sale/SaleItem → StockMovement(OUT) avtomatik — trade/views.py da
  SaleReturn.confirmed → StockMovement(IN) avtomatik — trade/views.py da
"""

from django.db import models


# ============================================================
# CHOICES
# ============================================================

class CustomerStatus(models.TextChoices):
    ACTIVE   = 'active',   'Faol'
    INACTIVE = 'inactive', 'Nofaol'


class PaymentType(models.TextChoices):
    CASH  = 'cash',  'Naqd'
    CARD  = 'card',  'Karta'
    MIXED = 'mixed', 'Aralash (naqd + karta)'
    DEBT  = 'debt',  'Nasiya'


class SaleStatus(models.TextChoices):
    COMPLETED = 'completed', 'Yakunlangan'
    CANCELLED = 'cancelled', 'Bekor qilingan'


# ============================================================
# MIJOZ GURUHI
# ============================================================

class CustomerGroup(models.Model):
    """
    Mijoz guruhi — chegirma guruhi.
    Har bir do'kon uchun alohida guruhlar (multi-tenant).
    """
    name       = models.CharField(
        max_length=100,
        verbose_name='Guruh nomi',
    )
    discount   = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name='Guruh chegirmasi (%)',
    )
    store      = models.ForeignKey(
        'store.Store',
        on_delete=models.CASCADE,
        related_name='customer_groups',
        verbose_name="Do'kon",
    )
    created_on = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Yaratilgan vaqti',
    )

    class Meta:
        verbose_name        = 'Mijoz guruhi'
        verbose_name_plural = 'Mijoz guruhlari'
        ordering            = ['name']
        unique_together     = [('store', 'name')]

    def __str__(self) -> str:
        return f"{self.name} ({self.discount}% chegirma)"


# ============================================================
# MIJOZ
# ============================================================

class Customer(models.Model):
    """
    Mijoz.
    Har bir mijoz bitta do'konga tegishli (multi-tenant).
    debt_balance — joriy nasiya qoldig'i. Sale.debt_amount qayta yangilanadi.
    Soft delete: status='inactive' ga o'tkaziladi.
    """
    name         = models.CharField(
        max_length=200,
        verbose_name='Ism-familiya',
    )
    phone        = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='Telefon',
    )
    address      = models.CharField(
        max_length=300,
        blank=True,
        verbose_name='Manzil',
    )
    debt_balance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name="Nasiya qoldig'i (so'm)",
    )
    group        = models.ForeignKey(
        CustomerGroup,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='customers',
        verbose_name='Mijoz guruhi',
    )
    store        = models.ForeignKey(
        'store.Store',
        on_delete=models.CASCADE,
        related_name='customers',
        verbose_name="Do'kon",
    )
    status       = models.CharField(
        max_length=10,
        choices=CustomerStatus.choices,
        default=CustomerStatus.ACTIVE,
        verbose_name='Holat',
    )
    created_on   = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Yaratilgan vaqti',
    )

    class Meta:
        verbose_name        = 'Mijoz'
        verbose_name_plural = 'Mijozlar'
        ordering            = ['name']

    def __str__(self) -> str:
        phone = self.phone or "tel yo'q"
        return f"{self.name} ({phone})"


# ============================================================
# SOTUV (SAVDO)
# ============================================================

class Sale(models.Model):
    """
    Sotuv yozuvi.

    ⚠️ Yaratish faqat @transaction.atomic bilan (trade/views.py).
    ⚠️ Yaratilganda har bir SaleItem uchun StockMovement(OUT) avtomatik.
    ⚠️ Bekor qilganda (PATCH .../cancel/) StockMovement(IN) avtomatik.
    ⚠️ Customer.debt_balance nasiya bo'lsa yangilanadi.

    paid_amount + debt_amount == total_price - discount_amount (validatsiya views.py da)
    """
    branch          = models.ForeignKey(
        'store.Branch',
        on_delete=models.PROTECT,
        related_name='sales',
        verbose_name='Filial',
    )
    store           = models.ForeignKey(
        'store.Store',
        on_delete=models.PROTECT,
        related_name='sales',
        verbose_name="Do'kon",
    )
    worker          = models.ForeignKey(
        'accaunt.Worker',
        on_delete=models.PROTECT,
        related_name='sales',
        verbose_name='Kassir',
    )
    customer        = models.ForeignKey(
        Customer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sales',
        verbose_name='Mijoz',
    )
    smena           = models.ForeignKey(
        'store.Smena',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sales',
        verbose_name='Smena',
    )
    payment_type    = models.CharField(
        max_length=10,
        choices=PaymentType.choices,
        verbose_name="To'lov turi",
    )
    total_price     = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name='Jami narx (chegirmasiz)',
    )
    discount_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name='Chegirma summasi',
    )
    paid_amount     = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name="To'langan summa",
    )
    debt_amount     = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name='Qarz summasi',
    )
    status          = models.CharField(
        max_length=15,
        choices=SaleStatus.choices,
        default=SaleStatus.COMPLETED,
        verbose_name='Holat',
    )
    description     = models.TextField(
        blank=True,
        verbose_name='Izoh',
    )
    created_on      = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Yaratilgan vaqti',
    )

    class Meta:
        verbose_name        = 'Sotuv'
        verbose_name_plural = 'Sotuvlar'
        ordering            = ['-created_on']

    def __str__(self) -> str:
        return f"Sotuv #{self.pk} — {self.branch.name} | {self.total_price} so'm"


# ============================================================
# SOTUV ELEMENTI
# ============================================================

class SaleItem(models.Model):
    """
    Sotuv tarkibidagi bitta mahsulot.
    O'zgartirilmaydi (immutable) — sotuv bekor qilinganda butun savdo bekor qilinadi.
    """
    sale        = models.ForeignKey(
        Sale,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Sotuv',
    )
    product     = models.ForeignKey(
        'warehouse.Product',
        on_delete=models.PROTECT,
        related_name='sale_items',
        verbose_name='Mahsulot',
    )
    quantity    = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        verbose_name='Miqdori',
    )
    unit_price  = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name='Savdo narxi (savdo paytida)',
    )
    total_price = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name='Jami (miqdor × narx)',
    )
    unit_cost   = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Tannarx (FIFO bo\'yicha, sotuv paytida)',
    )

    class Meta:
        verbose_name        = 'Sotuv elementi'
        verbose_name_plural = 'Sotuv elementlari'

    def __str__(self) -> str:
        return f"{self.product.name} × {self.quantity} = {self.total_price}"


# ============================================================
# QAYTARISH
# ============================================================

class SaleReturnStatus(models.TextChoices):
    PENDING   = 'pending',   'Kutilmoqda'
    CONFIRMED = 'confirmed', 'Tasdiqlangan'
    CANCELLED = 'cancelled', 'Bekor qilingan'


class SaleReturn(models.Model):
    """
    Sotuv qaytarish yozuvi.

    Holat o'tishi:
      pending   → confirmed  (manager tomonidan)
      pending   → cancelled  (manager tomonidan)
      confirmed → o'zgartirib bo'lmaydi (immutable)
      cancelled → o'zgartirib bo'lmaydi (immutable)

    ⚠️ Tasdiqlash (PATCH .../confirm/) faqat @transaction.atomic bilan:
       Har bir SaleReturnItem uchun StockMovement(IN) + Stock yangilanadi.
    ⚠️ sale(FK) ixtiyoriy — kassada chek yo'q bo'lsa ham qaytariladi.
    ⚠️ Customer.debt_balance qayta hisoblanadi (nasiya bo'lsa kamaytiriladi).
    """
    sale       = models.ForeignKey(
        Sale,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='returns',
        verbose_name='Asl sotuv',
    )
    branch     = models.ForeignKey(
        'store.Branch',
        on_delete=models.PROTECT,
        related_name='sale_returns',
        verbose_name='Filial',
    )
    store      = models.ForeignKey(
        'store.Store',
        on_delete=models.PROTECT,
        related_name='sale_returns',
        verbose_name="Do'kon",
    )
    worker     = models.ForeignKey(
        'accaunt.Worker',
        on_delete=models.PROTECT,
        related_name='sale_returns',
        verbose_name='Xodim',
    )
    customer   = models.ForeignKey(
        Customer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sale_returns',
        verbose_name='Mijoz',
    )
    smena      = models.ForeignKey(
        'store.Smena',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sale_returns',
        verbose_name='Smena',
    )
    reason     = models.TextField(
        blank=True,
        verbose_name='Qaytarish sababi',
    )
    total_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name='Jami qaytarilgan summa',
    )
    status     = models.CharField(
        max_length=10,
        choices=SaleReturnStatus.choices,
        default=SaleReturnStatus.PENDING,
        verbose_name='Holat',
    )
    created_on = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Yaratilgan vaqti',
    )

    class Meta:
        verbose_name        = 'Qaytarish'
        verbose_name_plural = 'Qaytarishlar'
        ordering            = ['-created_on']

    def __str__(self) -> str:
        return f"Qaytarish #{self.pk} — {self.branch.name} | {self.total_amount} so'm"


class SaleReturnItem(models.Model):
    """
    Qaytarish tarkibidagi bitta mahsulot.
    O'zgartirilmaydi (immutable).
    """
    sale_return = models.ForeignKey(
        SaleReturn,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Qaytarish',
    )
    product     = models.ForeignKey(
        'warehouse.Product',
        on_delete=models.PROTECT,
        related_name='return_items',
        verbose_name='Mahsulot',
    )
    quantity    = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        verbose_name='Miqdori',
    )
    unit_price  = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name='Birlik narxi',
    )
    total_price = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name='Jami (miqdor × narx)',
    )

    class Meta:
        verbose_name        = 'Qaytarish elementi'
        verbose_name_plural = 'Qaytarish elementlari'

    def __str__(self) -> str:
        return f"{self.product.name} × {self.quantity} = {self.total_price}"
