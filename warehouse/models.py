"""
============================================================
WAREHOUSE APP — Modellar
============================================================
Modellar:
  ProductUnit     — Mahsulot o'lchov birliklari (TextChoices)
  ProductStatus   — Mahsulot/kategoriya holati (TextChoices)
  MovementType    — Kirim/chiqim turi (TextChoices)
  TransferStatus  — Transfer holati (TextChoices)
  Category        — Mahsulot kategoriyasi
  SubCategory     — Mahsulot subkategoriyasi (ixtiyoriy, StoreSettings.subcategory_enabled)
  Currency        — Valyuta (UZS, USD, EUR, RUB, ...)
  ExchangeRate    — Valyuta kursi (CBU dan kunlik, Celery task)
  Product         — Mahsulot (nom, kategoriya, subkat, birlik, narx, shtrix-kod, valyuta)
  Warehouse       — Ombor (Anbar) — alohida saqlash joyi (Branch != Warehouse)
  Stock           — Filial YOKI Ombor bo'yicha qoldiq (Product + Branch|Warehouse + miqdor)
  StockMovement   — Kirim/chiqim tarixi (immutable log) + unit_cost (tannarx)
  Transfer        — Tovar ko'chirish (Filial↔Ombor↔Filial, guruhlab)
  TransferItem    — Transfer satri (1 Transfer → N mahsulot)
  StockBatch      — FIFO partiya (har bir IN harakati uchun, qty_left kamayadi)

Muhim farq:
  Branch (Filial)   — sotuv nuqtasi (kassa, sotuvchi).
  Warehouse (Anbar) — saqlash joyi (tovar keladi, filiallarga uzatiladi).
  Stock va StockMovement AYNAN bittasiga bog'lanadi:
    branch IS NOT NULL, warehouse IS NULL     → filial stoki
    branch IS NULL,     warehouse IS NOT NULL → ombor stoki

Transfer holatlari:
  pending   → yaratilgan, hali tasdiqlanmagan (stock o'zgarmaydi)
  confirmed → tasdiqlangan, stock yangilangan (immutable)
  cancelled → bekor qilingan (faqat pending dan)

FIFO (StockBatch):
  Har bir IN StockMovement uchun StockBatch yaratiladi.
  Chiqimda (OUT, Sotuv, Transfer.confirm) eng eski batch dan boshlab yechiladi.
  batch_code: {DO'KON[:5].upper()}-{YY}-{MM}-{DD}-{seq:04d}
  Misol: BESTM-26-03-10-0001
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


class TransferStatus(models.TextChoices):
    PENDING   = 'pending',   'Kutilmoqda'
    CONFIRMED = 'confirmed', 'Tasdiqlangan'
    CANCELLED = 'cancelled', 'Bekor qilingan'


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
    unit_cost     = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Tannarx (birlik)"
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


# ============================================================
# TOVAR KO'CHIRISH (TRANSFER)
# ============================================================

class Transfer(models.Model):
    """
    Tovar ko'chirish — bir joydan ikkinchi joyga mahsulotlar guruhi.

    Yo'nalishlar (barchasi qo'llab-quvvatlanadi):
      Ombor  → Filial   (eng ko'p ishlatiladigan)
      Filial → Ombor    (qaytarish)
      Ombor  → Ombor    (ichki ko'chirish)
      Filial → Filial   (filiallar o'rtasida)

    Holatlari:
      pending   → yaratilgan, tasdiqlanmagan.
                  Stock o'ZGARMAYDI. Xato bo'lsa bekor qilish mumkin.
      confirmed → TASDIQLANGAN. Stock yangilangan (OUT + IN).
                  Immutable — o'zgartirib bo'lmaydi.
      cancelled → Bekor qilingan (faqat pending dan).
                  Stock o'zgarmaydi.

    Constraint:
      from_branch XOR from_warehouse — manbaa (aynan bittasi)
      to_branch   XOR to_warehouse   — manzil (aynan bittasi)
      from != to  — o'ziga o'zi jo'natib bo'lmaydi
    """
    from_branch    = models.ForeignKey(
        Branch,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='transfers_out',
        verbose_name="Manbaa filial"
    )
    from_warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='transfers_out',
        verbose_name="Manbaa ombor"
    )
    to_branch      = models.ForeignKey(
        Branch,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='transfers_in',
        verbose_name="Manzil filial"
    )
    to_warehouse   = models.ForeignKey(
        Warehouse,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='transfers_in',
        verbose_name="Manzil ombor"
    )
    store          = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name='transfers',
        verbose_name="Do'koni"
    )
    worker         = models.ForeignKey(
        'accaunt.Worker',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transfers',
        verbose_name="Hodim"
    )
    status         = models.CharField(
        max_length=15,
        choices=TransferStatus.choices,
        default=TransferStatus.PENDING,
        verbose_name="Holati"
    )
    note           = models.TextField(
        blank=True,
        verbose_name="Izoh"
    )
    confirmed_at   = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Tasdiqlangan vaqti"
    )
    created_on     = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Yaratilgan vaqti"
    )

    class Meta:
        verbose_name        = "Ko'chirish"
        verbose_name_plural = "Ko'chirishlar"
        ordering            = ['-created_on']
        constraints         = [
            CheckConstraint(
                check=(
                    Q(from_branch__isnull=False, from_warehouse__isnull=True) |
                    Q(from_branch__isnull=True,  from_warehouse__isnull=False)
                ),
                name='transfer_from_branch_xor_warehouse',
            ),
            CheckConstraint(
                check=(
                    Q(to_branch__isnull=False, to_warehouse__isnull=True) |
                    Q(to_branch__isnull=True,  to_warehouse__isnull=False)
                ),
                name='transfer_to_branch_xor_warehouse',
            ),
        ]

    def __str__(self) -> str:
        from_loc = self.from_branch.name if self.from_branch_id else self.from_warehouse.name
        to_loc   = self.to_branch.name   if self.to_branch_id   else self.to_warehouse.name
        return f"Transfer #{self.id}: {from_loc} → {to_loc} ({self.get_status_display()})"


class TransferItem(models.Model):
    """
    Transfer satri — bitta mahsulot, bitta miqdor.

    Transfer tasdiqlangandan keyin immutable:
      - Stock harakat yozuvlari (StockMovement) yaratiladi
      - Qoldiqlar yangilanadi
      - TransferItem o'zgartirilmaydi va o'chirilmaydi

    Xato tuzatish: yangi Transfer yaratilib, teskari yo'nalishda jo'natiladi.
    """
    transfer  = models.ForeignKey(
        Transfer,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name="Transfer"
    )
    product   = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='transfer_items',
        verbose_name="Mahsulot"
    )
    quantity  = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        verbose_name="Miqdori"
    )
    note      = models.TextField(
        blank=True,
        verbose_name="Izoh"
    )

    class Meta:
        verbose_name        = "Transfer satri"
        verbose_name_plural = "Transfer satrlari"
        ordering            = ['id']

    def __str__(self) -> str:
        return f"{self.product.name} × {self.quantity}"


# ============================================================
# FIFO PARTIYASI (STOCKBATCH)
# ============================================================

class StockBatch(models.Model):
    """
    Har bir kelgan mahsulot partiyasi (FIFO uchun).

    Har bir IN StockMovement uchun avtomatik yaratiladi.
    Chiqimda (OUT harakat, Sotuv, Transfer.confirm) eng eski partiyadan
    boshlab qty_left kamayadi.

    Immutable maydonlar (yaratilgandan keyin o'zgartirilmaydi):
      batch_code, product, branch|warehouse, unit_cost, qty_received, movement

    O'zgaruvchi maydon:
      qty_left — FIFO da kamayadi (0 gacha)

    batch_code formati: {DO'KON[:5].upper()}-{YY}-{MM}-{DD}-{seq:04d}
    Misol: BESTM-26-03-10-0001
      BESTM — "Best Market" do'koni nomi (5 ta harf)
      26-03-10 — 2026-yil 10-mart (qisqa format)
      0001 — shu kun uchun birinchi partiya

    Constraint: branch va warehouse dan AYNAN bittasi to'ldirilishi SHART
      (Stock va StockMovement bilan bir xil pattern).
    """
    batch_code   = models.CharField(
        max_length=30,
        unique=True,
        verbose_name='Partiya kodi',
    )
    product      = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='batches',
        verbose_name='Mahsulot',
    )
    branch       = models.ForeignKey(
        Branch,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='batches',
        verbose_name='Filial',
    )
    warehouse    = models.ForeignKey(
        Warehouse,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='batches',
        verbose_name='Ombor',
    )
    unit_cost    = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name='Tannarx (birlik)',
    )
    qty_received = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        verbose_name='Qabul qilingan miqdor',
    )
    qty_left     = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        verbose_name='Qoldiq miqdor',
    )
    movement     = models.OneToOneField(
        StockMovement,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='batch',
        verbose_name='Kirim harakati',
    )
    store        = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name='batches',
        verbose_name="Do'koni",
    )
    received_at  = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Qabul vaqti',
    )

    class Meta:
        verbose_name        = 'Partiya'
        verbose_name_plural = 'Partiyalar'
        ordering            = ['received_at', 'id']  # FIFO tartibi: eng eski birinchi
        constraints         = [
            CheckConstraint(
                check=(
                    Q(branch__isnull=False, warehouse__isnull=True) |
                    Q(branch__isnull=True,  warehouse__isnull=False)
                ),
                name='batch_branch_xor_warehouse',
            )
        ]

    def __str__(self) -> str:
        location = self.branch.name if self.branch_id else self.warehouse.name
        return f"{self.batch_code}: {self.product.name} @ {location} — qoldiq: {self.qty_left}"
