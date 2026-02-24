"""
============================================================
WAREHOUSE APP — Modellar
============================================================
Modellar:
  ProductUnit     — Mahsulot o'lchov birliklari (TextChoices)
  ProductStatus   — Mahsulot/kategoriya holati (TextChoices)
  MovementType    — Kirim/chiqim turi (TextChoices)
  Category        — Mahsulot kategoriyasi
  Product         — Mahsulot (nom, kategoriya, birlik, narx, shtrix-kod)
  Stock           — Filial bo'yicha qoldiq (Product + Branch + miqdor)
  StockMovement   — Kirim/chiqim tarixi
"""

from django.db import models

from store.models import Branch, Store


# ============================================================
# CHOICES
# ============================================================

class ProductUnit(models.TextChoices):
    DONA   = 'dona',   'Dona'
    KG     = 'kg',     'Kilogram'
    GRAM   = 'g',      'Gram'
    LITR   = 'litr',   'Litr'
    METR   = 'metr',   'Metr'
    M2     = 'm2',     'Kvadrat metr'
    YASHIK = 'yashik', 'Yashik'
    QOP    = 'qop',    'Qop'


class ProductStatus(models.TextChoices):
    ACTIVE   = 'active',   'Faol'
    INACTIVE = 'inactive', 'Nofaol'


class MovementType(models.TextChoices):
    IN  = 'in',  'Kirim'
    OUT = 'out', 'Chiqim'


# ============================================================
# KATEGORIYA
# ============================================================

class Category(models.Model):
    """
    Mahsulot kategoriyasi.
    Har bir kategoriya bitta do'konga tegishli (multi-tenant).
    Soft delete — o'chirish o'rniga status='inactive' ga o'tkaziladi.
    """
    name        = models.CharField(
        max_length=200,
        verbose_name="Nomi"
    )
    description = models.TextField(
        blank=True,
        verbose_name="Tavsifi"
    )
    store       = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name='categories',
        verbose_name="Do'koni"
    )
    status      = models.CharField(
        max_length=10,
        choices=ProductStatus.choices,
        default=ProductStatus.ACTIVE,
        verbose_name="Holati"
    )
    created_on  = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Yaratilgan vaqti"
    )

    class Meta:
        verbose_name        = 'Kategoriya'
        verbose_name_plural = 'Kategoriyalar'
        ordering            = ['name']
        unique_together     = [('store', 'name')]

    def __str__(self) -> str:
        return self.name


# ============================================================
# MAHSULOT
# ============================================================

class Product(models.Model):
    """
    Mahsulot.
    Har bir mahsulot bitta do'konga tegishli (multi-tenant).
    Kategoriyaga biriktirilgan (ixtiyoriy).
    Soft delete — o'chirish o'rniga status='inactive' ga o'tkaziladi.

    Shtrix-kod: do'kon ichida unikal (null=True — bir nechta null ruxsat).
    """
    name           = models.CharField(
        max_length=300,
        verbose_name="Nomi"
    )
    category       = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products',
        verbose_name="Kategoriyasi"
    )
    unit           = models.CharField(
        max_length=10,
        choices=ProductUnit.choices,
        default=ProductUnit.DONA,
        verbose_name="O'lchov birligi"
    )
    purchase_price = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        verbose_name="Xarid narxi (UZS)"
    )
    sale_price     = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        verbose_name="Sotish narxi (UZS)"
    )
    barcode        = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Shtrix-kod"
    )
    store          = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name='products',
        verbose_name="Do'koni"
    )
    status         = models.CharField(
        max_length=10,
        choices=ProductStatus.choices,
        default=ProductStatus.ACTIVE,
        verbose_name="Holati"
    )
    created_on     = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Yaratilgan vaqti"
    )

    class Meta:
        verbose_name        = 'Mahsulot'
        verbose_name_plural = 'Mahsulotlar'
        ordering            = ['name']

    def __str__(self) -> str:
        return f"{self.name} ({self.get_unit_display()})"


# ============================================================
# OMBOR QOLDIG'I
# ============================================================

class Stock(models.Model):
    """
    Filial bo'yicha mahsulot qoldig'i.
    Har bir mahsulot-filial juftligi uchun bitta yozuv.
    StockMovement yaratilganda avtomatik yangilanadi.
    """
    product    = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='stocks',
        verbose_name="Mahsulot"
    )
    branch     = models.ForeignKey(
        Branch,
        on_delete=models.CASCADE,
        related_name='stocks',
        verbose_name="Filial"
    )
    quantity   = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        default=0,
        verbose_name="Qoldiq miqdori"
    )
    updated_on = models.DateTimeField(
        auto_now=True,
        verbose_name="Yangilangan vaqti"
    )

    class Meta:
        verbose_name        = "Ombor qoldig'i"
        verbose_name_plural = "Ombor qoldiqlari"
        ordering            = ['product__name']
        unique_together     = [('product', 'branch')]

    def __str__(self) -> str:
        return f"{self.product.name} — {self.branch.name}: {self.quantity}"


# ============================================================
# KIRIM / CHIQIM HARAKATLARI
# ============================================================

class StockMovement(models.Model):
    """
    Mahsulot kirim/chiqim tarixi.
    Bu yozuvlar o'zgartirilmaydi va o'chirilmaydi (immutable log).
    Xatolikni tuzatish uchun qarama-qarshi harakat yarating.

    Yaratilganda Stock.quantity avtomatik yangilanadi (ViewSet.perform_create da).
    """
    product       = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='movements',
        verbose_name="Mahsulot"
    )
    branch        = models.ForeignKey(
        Branch,
        on_delete=models.CASCADE,
        related_name='movements',
        verbose_name="Filial"
    )
    movement_type = models.CharField(
        max_length=10,
        choices=MovementType.choices,
        verbose_name="Harakat turi"
    )
    quantity      = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        verbose_name="Miqdori"
    )
    note          = models.TextField(
        blank=True,
        verbose_name="Izoh"
    )
    worker        = models.ForeignKey(
        'accaunt.Worker',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='movements',
        verbose_name="Hodim"
    )
    created_on    = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Vaqti"
    )

    class Meta:
        verbose_name        = 'Harakat'
        verbose_name_plural = 'Harakatlar'
        ordering            = ['-created_on']

    def __str__(self) -> str:
        return (
            f"{self.get_movement_type_display()} — "
            f"{self.product.name} × {self.quantity} "
            f"({self.branch.name})"
        )
