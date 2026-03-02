"""
============================================================
WAREHOUSE APP — Modellar
============================================================
Modellar:
  ProductUnit     — Mahsulot o'lchov birliklari (TextChoices)
  ProductStatus   — Mahsulot/kategoriya holati (TextChoices)
  MovementType    — Kirim/chiqim/ko'chirish turi (TextChoices)
  Category        — Mahsulot kategoriyasi
  Product         — Mahsulot (nom, kategoriya, birlik, narx, shtrix-kod)
  Warehouse       — Alohida ombor joylashuvi (do'konning fizik ombori)
  Stock           — Filial yoki ombor bo'yicha qoldiq (Product + joylashuv + miqdor)
  StockMovement   — Kirim/chiqim/ko'chirish tarixi (immutable log)
"""

from django.db import models
from django.db.models import Q

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
    IN       = 'in',       'Kirim'
    OUT      = 'out',      'Chiqim'
    TRANSFER = 'transfer', "Ko'chirish"


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
        unique_together     = [('store', 'name'), ('store', 'barcode')]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_unit_display()})"


# ============================================================
# OMBOR (ALOHIDA FIZIK JOY)
# ============================================================

class Warehouse(models.Model):
    """
    Do'konning alohida ombor joylashuvi.
    Filialdan farqi: bu mahsulot saqlanadigan fizik joy,
    sotish emas. Mahsulot avval omborga keladi, so'ng
    filiallarga tarqatiladi.

    Multi-tenant: har bir ombor bitta do'konga tegishli.
    Soft delete — status='inactive' ga o'tkaziladi.
    """
    name       = models.CharField(
        max_length=200,
        verbose_name="Nomi"
    )
    store      = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name='warehouses',
        verbose_name="Do'koni"
    )
    address    = models.CharField(
        max_length=300,
        blank=True,
        verbose_name="Manzili"
    )
    status     = models.CharField(
        max_length=10,
        choices=ProductStatus.choices,
        default=ProductStatus.ACTIVE,
        verbose_name="Holati"
    )
    created_on = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Yaratilgan vaqti"
    )

    class Meta:
        verbose_name        = 'Ombor'
        verbose_name_plural = 'Omborlar'
        ordering            = ['name']
        unique_together     = [('store', 'name')]

    def __str__(self) -> str:
        return f"{self.name} ({self.store.name})"


# ============================================================
# QOLDIQ (FILIAL YOKI OMBOR BO'YICHA)
# ============================================================

class Stock(models.Model):
    """
    Mahsulot qoldig'i — filial yoki ombor bo'yicha.
    branch yoki warehouse dan biri albatta bo'lishi kerak (ikkalasi ham emas).

    StockMovement yaratilganda avtomatik yangilanadi.
    Boshlang'ich inventarizatsiya uchun to'g'ridan-to'g'ri POST qilish mumkin.
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
        null=True,
        blank=True,
        verbose_name="Filial"
    )
    warehouse  = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name='stocks',
        null=True,
        blank=True,
        verbose_name="Ombor"
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
        verbose_name        = "Qoldiq"
        verbose_name_plural = "Qoldiqlar"
        ordering            = ['product__name']
        unique_together     = [('product', 'branch'), ('product', 'warehouse')]
        constraints         = [
            models.CheckConstraint(
                check=(
                    Q(branch__isnull=False, warehouse__isnull=True) |
                    Q(branch__isnull=True,  warehouse__isnull=False)
                ),
                name='stock_exactly_one_location',
            ),
        ]

    def __str__(self) -> str:
        location = self.branch.name if self.branch_id else self.warehouse.name
        return f"{self.product.name} — {location}: {self.quantity}"


# ============================================================
# KIRIM / CHIQIM / KO'CHIRISH HARAKATLARI
# ============================================================

class StockMovement(models.Model):
    """
    Mahsulot harakati tarixi (kirim, chiqim, ko'chirish).
    Bu yozuvlar o'zgartirilmaydi va o'chirilmaydi (immutable log).
    Xatolikni tuzatish uchun qarama-qarshi harakat yarating.

    Harakat turlari:
      IN       — tashqaridan kirim (from_* bo'sh, to_* to'ldiriladi)
      OUT      — tashqariga chiqim/sotish (from_* to'ldiriladi, to_* bo'sh)
      TRANSFER — joy o'zgarishi (from_* va to_* ikkalasi ham to'ldiriladi)

    Yaratilganda Stock.quantity avtomatik yangilanadi (ViewSet.perform_create da).
    """
    product        = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='movements',
        verbose_name="Mahsulot"
    )
    movement_type  = models.CharField(
        max_length=10,
        choices=MovementType.choices,
        verbose_name="Harakat turi"
    )
    quantity       = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        verbose_name="Miqdori"
    )
    # Qayerdan (IN da bo'sh)
    from_branch    = models.ForeignKey(
        Branch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='movements_from',
        verbose_name="Filialdan"
    )
    from_warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='movements_from',
        verbose_name="Ombordan"
    )
    # Qayerga (OUT da bo'sh)
    to_branch      = models.ForeignKey(
        Branch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='movements_to',
        verbose_name="Filialga"
    )
    to_warehouse   = models.ForeignKey(
        Warehouse,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='movements_to',
        verbose_name="Omborga"
    )
    note           = models.TextField(
        blank=True,
        verbose_name="Izoh"
    )
    worker         = models.ForeignKey(
        'accaunt.Worker',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='movements',
        verbose_name="Hodim"
    )
    created_on     = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Vaqti"
    )

    class Meta:
        verbose_name        = 'Harakat'
        verbose_name_plural = 'Harakatlar'
        ordering            = ['-created_on']

    def __str__(self) -> str:
        from_loc = getattr(self.from_branch or self.from_warehouse, 'name', '—')
        to_loc   = getattr(self.to_branch   or self.to_warehouse,   'name', '—')
        return (
            f"{self.get_movement_type_display()} — "
            f"{self.product.name} × {self.quantity} "
            f"({from_loc} → {to_loc})"
        )
