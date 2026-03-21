"""
============================================================
STORE APP — Modellar
============================================================
Modellar:
  StoreStatus    — Do'kon va filial holatlari (TextChoices)
  Store          — Do'kon
  Branch         — Filial (do'konga biriktirilgan)
  StoreSettings  — Do'kon sozlamalari (OneToOne → Store)
                   BOSQICH 2: 10 guruh, 30+ maydon
                   Signal orqali Store yaratilganda avtomatik yaratiladi (QOIDA 1)
                   Redis keshi orqali tez yuklash (QOIDA 3)
  SmenaStatus    — Smena holatlari: open | closed (BOSQICH 3)
  Smena          — Kassir smenasi (BOSQICH 3)
                   Har bir filial uchun bir vaqtda faqat bitta OPEN smena
                   shift_enabled=True bo'lsa sotuv smena mavjud bo'lganda mumkin
"""

from django.db import models


# ============================================================
# STATUS CHOICES
# ============================================================

class StoreStatus(models.TextChoices):
    ACTIVE   = 'active',   'Faol'
    INACTIVE = 'inactive', 'Nofaol'


class DefaultCurrency(models.TextChoices):
    UZS = 'UZS', "O'zbek so'mi (UZS)"
    USD = 'USD', 'Amerika dollari (USD)'
    RUB = 'RUB', 'Rossiya rubli (RUB)'
    EUR = 'EUR', 'Yevropa yevrosi (EUR)'
    CNY = 'CNY', 'Xitoy yuani (CNY)'


# ============================================================
# DO'KON MODELI
# ============================================================

class Store(models.Model):
    """
    Do'kon modeli.
    Har bir do'konning o'ziga xos xodimlari va filiallari bo'ladi.
    """
    name       = models.CharField(
        max_length=200,
        verbose_name="Do'kon nomi"
    )
    address    = models.CharField(
        max_length=300,
        blank=True,
        verbose_name="Manzil"
    )
    phone      = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="Telefon"
    )
    status     = models.CharField(
        max_length=10,
        choices=StoreStatus.choices,
        default=StoreStatus.ACTIVE,
        verbose_name="Holati"
    )
    created_on = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Yaratilgan vaqti"
    )

    class Meta:
        verbose_name        = "Do'kon"
        verbose_name_plural = "Do'konlar"
        ordering            = ['-created_on']

    def __str__(self) -> str:
        return self.name


# ============================================================
# FILIAL MODELI
# ============================================================

class Branch(models.Model):
    """
    Filial modeli.
    Har bir filial bitta do'konga tegishli.
    Xodimlar filialga biriktiriladi.
    """
    store      = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name='branches',
        null=True,
        blank=True,
        verbose_name="Do'koni"
    )
    name       = models.CharField(
        max_length=200,
        verbose_name="Filial nomi"
    )
    address    = models.CharField(
        max_length=300,
        blank=True,
        verbose_name="Manzil"
    )
    phone      = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="Telefon"
    )
    status     = models.CharField(
        max_length=10,
        choices=StoreStatus.choices,
        default=StoreStatus.ACTIVE,
        verbose_name="Holati"
    )
    created_on = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Yaratilgan vaqti"
    )

    class Meta:
        verbose_name        = 'Filial'
        verbose_name_plural = 'Filiallar'
        ordering            = ['-created_on']
        unique_together     = [('store', 'name')]

    def __str__(self) -> str:
        return f"{self.name} ({self.store.name if self.store else '—'})"


# ============================================================
# DO'KON SOZLAMALARI — BOSQICH 2
# ============================================================

class StoreSettings(models.Model):
    """
    Do'kon sozlamalari.
    Har bir do'kon uchun bitta yozuv (OneToOneField).

    ⚠️ QOIDA 1: Store yaratilganda signal orqali AVTOMATIK yaratiladi.
                store/signals.py → post_save signal.
    ⚠️ QOIDA 2: Doim select_related('store__settings') bilan tortish.
    ⚠️ QOIDA 3: get_store_settings(store_id) — Redis kesh (5 daqiqa TTL).
                config/cache_utils.py → get_store_settings().

    10 guruh:
      1. Modul on/off flaglari (ixtiyoriy funksiyalar)
      2. Valyuta sozlamalari
      3. To'lov sozlamalari
      4. Chegirma sozlamalari
      5. Chek sozlamalari
      6. Ombor sozlamalari
      7. Smena sozlamalari
      8. Telegram sozlamalari
      9. Soliq / OFD sozlamalari (v2)
     10. Yetkazib beruvchi sozlamalari (v2)
    """

    store = models.OneToOneField(
        Store,
        on_delete=models.CASCADE,
        related_name='settings',
        verbose_name="Do'kon"
    )

    # ============================================================
    # GURUH 1 — Modul on/off flaglari
    # ============================================================
    # SubCategory (BOSQICH 1.1) — kichik do'konlarda off
    subcategory_enabled   = models.BooleanField(
        default=False,
        verbose_name="Subkategoriya moduli"
    )
    # SaleReturn (BOSQICH 5) — aksariyat do'konlarda on
    sale_return_enabled   = models.BooleanField(
        default=True,
        verbose_name="Qaytarish moduli"
    )
    # WastageRecord (BOSQICH 7) — on, lekin ishlatmaslik mumkin
    wastage_enabled       = models.BooleanField(
        default=True,
        verbose_name="Isrof moduli"
    )
    # StockAudit (BOSQICH 8) — on
    stock_audit_enabled   = models.BooleanField(
        default=True,
        verbose_name="Inventarizatsiya moduli"
    )
    # WorkerKPI (BOSQICH 9) — faqat xohlagan owner yoqadi
    kpi_enabled           = models.BooleanField(
        default=False,
        verbose_name="KPI moduli"
    )
    # PriceList (BOSQICH 12) — faqat ulgurji/retail farq uchun
    price_list_enabled    = models.BooleanField(
        default=False,
        verbose_name="Narx ro'yxati moduli"
    )

    # ============================================================
    # GURUH 2 — Valyuta sozlamalari
    # ============================================================
    default_currency      = models.CharField(
        max_length=3,
        choices=DefaultCurrency.choices,
        default=DefaultCurrency.UZS,
        verbose_name="Asosiy valyuta"
    )
    show_usd_price        = models.BooleanField(
        default=False,
        verbose_name="USD narxini ko'rsatish"
    )
    show_rub_price        = models.BooleanField(
        default=False,
        verbose_name="RUB narxini ko'rsatish"
    )
    show_eur_price        = models.BooleanField(
        default=False,
        verbose_name="EUR narxini ko'rsatish"
    )
    show_cny_price        = models.BooleanField(
        default=False,
        verbose_name="CNY narxini ko'rsatish"
    )

    # ============================================================
    # GURUH 3 — To'lov sozlamalari
    # ============================================================
    allow_cash            = models.BooleanField(
        default=True,
        verbose_name="Naqd to'lov"
    )
    allow_card            = models.BooleanField(
        default=True,
        verbose_name="Karta to'lov"
    )
    allow_debt            = models.BooleanField(
        default=False,
        verbose_name="Nasiya (qarz)"
    )

    # ============================================================
    # GURUH 4 — Chegirma sozlamalari
    # ============================================================
    allow_discount        = models.BooleanField(
        default=True,
        verbose_name="Chegirma berish ruxsati"
    )
    max_discount_percent  = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name="Maksimal chegirma foizi (0 = cheksiz)"
    )

    # ============================================================
    # GURUH 5 — Chek sozlamalari
    # ============================================================
    receipt_header        = models.TextField(
        blank=True,
        verbose_name="Chek yuqori matni"
    )
    receipt_footer        = models.TextField(
        blank=True,
        verbose_name="Chek pastki matni"
    )
    show_store_logo       = models.BooleanField(
        default=False,
        verbose_name="Chekda do'kon logosi"
    )
    show_worker_name      = models.BooleanField(
        default=True,
        verbose_name="Chekda kassir ismi"
    )

    # ============================================================
    # GURUH 6 — Ombor sozlamalari
    # ============================================================
    low_stock_enabled     = models.BooleanField(
        default=True,
        verbose_name="Kam qoldiq ogohlantirish"
    )
    low_stock_threshold   = models.PositiveIntegerField(
        default=5,
        verbose_name="Ogohlantirish chegarasi (dona)"
    )

    # ============================================================
    # GURUH 7 — Smena sozlamalari (BOSQICH 3)
    # ============================================================
    shift_enabled         = models.BooleanField(
        default=False,
        verbose_name="Smena tizimi"
    )
    shifts_per_day        = models.PositiveSmallIntegerField(
        default=1,
        verbose_name="Kunlik smena soni (1/2/3)"
    )
    require_cash_count    = models.BooleanField(
        default=False,
        verbose_name="Smena ochish/yopishda naqd hisoblash majburiy"
    )

    # ============================================================
    # GURUH 8 — Telegram sozlamalari (BOSQICH 11)
    # ============================================================
    telegram_enabled      = models.BooleanField(
        default=False,
        verbose_name="Telegram bildirishnomalar"
    )
    telegram_chat_id      = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="Telegram chat ID"
    )

    # ============================================================
    # GURUH 9 — Soliq / OFD sozlamalari (v2 — BOSQICH 14)
    # ============================================================
    tax_enabled           = models.BooleanField(
        default=False,
        verbose_name="QQS (soliq)"
    )
    tax_percent           = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=12,
        verbose_name="QQS foizi (O'zbekistonda 12%)"
    )
    ofd_enabled           = models.BooleanField(
        default=False,
        verbose_name="OFD integratsiya (v2)"
    )
    ofd_token             = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="OFD token"
    )
    ofd_device_id         = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="OFD qurilma ID"
    )

    # ============================================================
    # GURUH 10 — Yetkazib beruvchi sozlamalari (v2 — BOSQICH 13)
    # ============================================================
    supplier_credit_enabled = models.BooleanField(
        default=False,
        verbose_name="Yetkazib beruvchi qarz hisobi"
    )

    # ============================================================
    # GURUH 11 — Export sozlamalari (BOSQICH 16)
    # ============================================================
    auto_pdf_on_smena_close = models.BooleanField(
        default=False,
        verbose_name="Smena yopilganda Z-report PDF avtomatik generatsiya"
    )

    class Meta:
        verbose_name        = "Do'kon sozlamalari"
        verbose_name_plural = "Do'kon sozlamalari"

    def __str__(self) -> str:
        return f"{self.store.name} — sozlamalari"


# ============================================================
# SMENA — BOSQICH 3
# ============================================================

class SmenaStatus(models.TextChoices):
    OPEN   = 'open',   'Ochiq'
    CLOSED = 'closed', 'Yopiq'


class Smena(models.Model):
    """
    Kassir smenasi.

    ⚠️ QOIDA: Bir filialda bir vaqtda faqat bitta OPEN smena bo'lishi shart.
               Bu views.py da perform_create da tekshiriladi.

    ⚠️ Multi-tenant: store FK — worker.store_id bilan to'g'ridan-to'g'ri
               filtrlash uchun (branch__store JOIN qilmasdan).

    ⚠️ shift_enabled=True bo'lsa sotuv faqat OPEN smena mavjud bo'lganda
               bajarilishi mumkin (BOSQICH 4 da tekshiriladi).

    Hisobotlar:
      X-report — smena davomidagi hisobot (smena yopilmaydi)
      Z-report — smenani yopadi + yakuniy hisobot
                 (BOSQICH 4/6 da Sale/Expense qo'shilgandan keyin to'ldiriladi)
    """
    branch = models.ForeignKey(
        'Branch',
        on_delete=models.PROTECT,
        related_name='smenas',
        verbose_name='Filial',
    )
    store = models.ForeignKey(
        'Store',
        on_delete=models.PROTECT,
        related_name='smenas',
        verbose_name="Do'kon",
    )
    worker_open = models.ForeignKey(
        'accaunt.Worker',
        on_delete=models.PROTECT,
        related_name='opened_smenas',
        verbose_name='Smena ochgan xodim',
    )
    worker_close = models.ForeignKey(
        'accaunt.Worker',
        on_delete=models.PROTECT,
        related_name='closed_smenas',
        null=True,
        blank=True,
        verbose_name='Smena yopgan xodim',
    )
    start_time = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Boshlanish vaqti',
    )
    end_time = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Tugash vaqti',
    )
    status = models.CharField(
        max_length=10,
        choices=SmenaStatus.choices,
        default=SmenaStatus.OPEN,
        verbose_name='Holat',
    )
    cash_start = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name="Boshlang'ich naqd (so'm)",
    )
    cash_end = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Yakuniy naqd (so'm)",
    )
    description = models.TextField(
        blank=True,
        verbose_name='Izoh',
    )

    class Meta:
        verbose_name        = 'Smena'
        verbose_name_plural = 'Smenalar'
        ordering            = ['-start_time']

    def __str__(self) -> str:
        return f"Smena #{self.pk} — {self.branch.name} ({self.get_status_display()})"
