"""
============================================================
WAREHOUSE APP — Modellar
============================================================
Modellar:
  ProductUnit     — Mahsulot o'lchov birliklari (TextChoices)
  ProductStatus   — Mahsulot/kategoriya holati (TextChoices)
  MovementType    — Kirim/chiqim turi (TextChoices)
  Category        — Mahsulot kategoriyasi
  SubCategory     — Mahsulot subkategoriyasi (ixtiyoriy, StoreSettings.subcategory_enabled)
  Currency        — Valyuta (UZS, USD, EUR, RUB, ...)
  ExchangeRate    — Valyuta kursi (CBU dan kunlik, Celery task)
  Product         — Mahsulot (nom, kategoriya, subkat, birlik, narx, shtrix-kod, valyuta)
  Warehouse       — Ombor (Anbar) — alohida saqlash joyi (Branch != Warehouse)
  Stock           — Filial YOKI Ombor bo'yicha qoldiq (Product + Branch|Warehouse + miqdor)
  StockMovement   — Kirim/chiqim tarixi (immutable log)

Muhim farq:
  Branch (Filial)   — sotuv nuqtasi (kassa, sotuvchi).
  Warehouse (Anbar) — saqlash joyi (tovar keladi, filiallarga uzatiladi).
  Stock va StockMovement AYNAN bittasiga bog'lanadi:
    branch IS NOT NULL, warehouse IS NULL     → filial stoki
    branch IS NULL,     warehouse IS NOT NULL → ombor stoki
"""

from django.db import models
from django.db.models import Q, CheckConstraint

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
    QUTI   = 'quti',   'Quti'


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
# SUBKATEGORIYA (ixtiyoriy — StoreSettings.subcategory_enabled)
# ============================================================

class SubCategory(models.Model):
    """
    Mahsulot subkategoriyasi.
    Ierarxiya: Category → SubCategory → Product (ixtiyoriy).

    StoreSettings.subcategory_enabled = True bo'lganda frontend ko'rsatadi.
    False bo'lganda endpoint mavjud lekin Product.subcategory null qoladi.

    Unikal shart: bir do'konda bir kategoriya ichida bir xil nom bo'lmaydi.
    """
    name        = models.CharField(
        max_length=200,
        verbose_name="Nomi"
    )
    description = models.TextField(
        blank=True,
        verbose_name="Tavsifi"
    )
    category    = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='subcategories',
        verbose_name="Kategoriyasi"
    )
    store       = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name='subcategories',
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
        verbose_name        = 'Subkategoriya'
        verbose_name_plural = 'Subkategoriyalar'
        ordering            = ['name']
        unique_together     = [('store', 'category', 'name')]

    def __str__(self) -> str:
        return f"{self.category.name} → {self.name}"


# ============================================================
# VALYUTA
# ============================================================

class Currency(models.Model):
    """
    Valyuta modeli.
    UZS — asosiy valyuta (is_base=True).
    Boshqa valyutalar (USD, EUR, RUB, CNY) ExchangeRate orqali UZS ga o'tkaziladi.

    Dastlabki valyutalar migration 0005 da seed qilinadi:
      UZS (asosiy), USD, EUR, RUB, CNY
    """
    code    = models.CharField(
        max_length=3,
        unique=True,
        verbose_name="Kod"
    )
    name    = models.CharField(
        max_length=100,
        verbose_name="Nomi"
    )
    symbol  = models.CharField(
        max_length=5,
        verbose_name="Belgisi"
    )
    is_base = models.BooleanField(
        default=False,
        verbose_name="Asosiy valyuta"
    )

    class Meta:
        verbose_name        = 'Valyuta'
        verbose_name_plural = 'Valyutalar'
        ordering            = ['code']

    def __str__(self) -> str:
        return f"{self.code} ({self.symbol})"


# ============================================================
# VALYUTA KURSI
# ============================================================

class ExchangeRate(models.Model):
    """
    Valyuta kursi.
    1 xorijiy valyuta = rate UZS (CBU rasmiy kursi).

    Har kun 09:00 da Celery task (warehouse.tasks.update_exchange_rates)
    orqali CBU API dan avtomatik yangilanadi:
    https://cbu.uz/uz/arkhiv-kursov-valyut/json/

    Unikal shart: bir valyuta bir kun uchun faqat bir kurs bo'ladi.
    """
    currency   = models.ForeignKey(
        Currency,
        on_delete=models.CASCADE,
        related_name='rates',
        verbose_name="Valyuta"
    )
    rate       = models.DecimalField(
        max_digits=16,
        decimal_places=4,
        verbose_name="Kurs (1 xorijiy = X UZS)"
    )
    date       = models.DateField(
        verbose_name="Sana"
    )
    source     = models.CharField(
        max_length=50,
        default='CBU',
        verbose_name="Manba"
    )
    created_on = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Yaratilgan vaqti"
    )

    class Meta:
        verbose_name        = 'Valyuta kursi'
        verbose_name_plural = 'Valyuta kurslari'
        ordering            = ['-date']
        unique_together     = [('currency', 'date')]

    def __str__(self) -> str:
        return f"{self.currency.code} — {self.date}: {self.rate} UZS"


# ============================================================
# MAHSULOT
# ============================================================

class Product(models.Model):
    """
    Mahsulot.
    Har bir mahsulot bitta do'konga tegishli (multi-tenant).
    Kategoriya va subkategoriyaga biriktirilgan (ixtiyoriy).
    Soft delete — o'chirish o'rniga status='inactive' ga o'tkaziladi.

    Shtrix-kod:
      - do'kon ichida unikal (null=True — bir nechta null ruxsat)
      - avtomatik generatsiya: EAN-13, prefix 2XXXXX (GS1 in-store)
      - ProductViewSet.perform_create da barcode yo'q bo'lsa auto-generate

    Narx valyutasi:
      - price_currency null bo'lsa → narx UZS da
      - null bo'lmasa → narx price_currency da, ExchangeRate orqali UZS konvertatsiya
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
    subcategory    = models.ForeignKey(
        SubCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products',
        verbose_name="Subkategoriyasi"
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
        verbose_name="Xarid narxi"
    )
    sale_price     = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        verbose_name="Sotish narxi"
    )
    price_currency = models.ForeignKey(
        Currency,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products',
        verbose_name="Narx valyutasi"
    )
    barcode        = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Shtrix-kod (EAN-13)"
    )
    image          = models.ImageField(
        upload_to='products/',
        null=True,
        blank=True,
        verbose_name="Rasm"
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
# OMBOR (ANBAR) — Alohida saqlash joyi
# ============================================================

class Warehouse(models.Model):
    """
    Ombor (Anbar) — mahsulotlar saqlanadigan alohida joy.

    Branch (Filial) dan farqi:
      - Filial  → sotuv nuqtasi (kassa bor, sotuvchi ishlaydi)
      - Ombor   → faqat saqlash (tovar keladi, filiallarga uzatiladi)

    Misol: 1 ta markaziy ombor → 3 ta filialga tovar uzatadi.

    Multi-tenant: har bir ombor bitta do'konga tegishli.
    Soft delete: is_active=False bilan nofaol qilinadi.
    Subscription: max_warehouses limiti shu modelga qarab hisoblanadi.
    """
    name       = models.CharField(
        max_length=200,
        verbose_name="Nomi"
    )
    address    = models.TextField(
        blank=True,
        verbose_name="Manzili"
    )
    store      = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name='warehouses',
        verbose_name="Do'koni"
    )
    is_active  = models.BooleanField(
        default=True,
        verbose_name="Faolmi"
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
# OMBOR QOLDIG'I
# ============================================================

class Stock(models.Model):
    """
    Mahsulot qoldig'i — filial YOKI omborда.

    Constraint: branch va warehouse dan AYNAN bittasi to'ldirilishi SHART.
      branch IS NOT NULL, warehouse IS NULL     → filial stoki
      branch IS NULL,     warehouse IS NOT NULL → ombor stoki

    unique_together:
      ('product', 'branch')    — bir filialda bir mahsulot faqat bir marta
      ('product', 'warehouse') — bir omborда bir mahsulot faqat bir marta
      NULL qiymatlar unique_together da hisobga olinmaydi (DB standarti).
      CheckConstraint esa NULL holat mantiqini nazorat qiladi.

    StockMovement yaratilganda avtomatik yangilanadi (ViewSet.perform_create).
    """
    product   = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='stocks',
        verbose_name="Mahsulot"
    )
    branch    = models.ForeignKey(
        Branch,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='stocks',
        verbose_name="Filial"
    )
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='stocks',
        verbose_name="Ombor"
    )
    quantity  = models.DecimalField(
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
        unique_together     = [('product', 'branch'), ('product', 'warehouse')]
        constraints         = [
            CheckConstraint(
                check=(
                    Q(branch__isnull=False, warehouse__isnull=True) |
                    Q(branch__isnull=True,  warehouse__isnull=False)
                ),
                name='stock_branch_xor_warehouse',
            )
        ]

    def __str__(self) -> str:
        location = self.branch.name if self.branch_id else self.warehouse.name
        return f"{self.product.name} — {location}: {self.quantity}"


# ============================================================
# KIRIM / CHIQIM HARAKATLARI
# ============================================================

class StockMovement(models.Model):
    """
    Mahsulot kirim/chiqim tarixi.
    Bu yozuvlar o'zgartirilmaydi va o'chirilmaydi (immutable log).
    Xatolikni tuzatish uchun qarama-qarshi harakat yarating.

    Constraint: branch va warehouse dan AYNAN bittasi to'ldirilishi SHART.
      branch IS NOT NULL, warehouse IS NULL     → filial harakati
      branch IS NULL,     warehouse IS NOT NULL → ombor harakati

    Yaratilganda Stock.quantity avtomatik yangilanadi (ViewSet.perform_create da).

    Muhim: Sale (sotuv) doim branch bilan bog'liq (kassada sodir bo'ladi).
    Ombor kirim/chiqim esa branch YOKI warehouse bilan bo'lishi mumkin.
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
        null=True,
        blank=True,
        related_name='movements',
        verbose_name="Filial"
    )
    warehouse     = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='movements',
        verbose_name="Ombor"
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
        constraints         = [
            CheckConstraint(
                check=(
                    Q(branch__isnull=False, warehouse__isnull=True) |
                    Q(branch__isnull=True,  warehouse__isnull=False)
                ),
                name='movement_branch_xor_warehouse',
            )
        ]

    def __str__(self) -> str:
        location = self.branch.name if self.branch_id else self.warehouse.name
        return (
            f"{self.get_movement_type_display()} — "
            f"{self.product.name} × {self.quantity} "
            f"({location})"
        )
