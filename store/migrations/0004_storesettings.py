"""
Migration 0004 — StoreSettings modeli

O'zgarishlar:
  1. StoreSettings modeli yaratildi (OneToOneField → Store)
     10 guruh, 30+ maydon

  ⚠️ ESLATMA: Mavjud do'konlar uchun StoreSettings avtomatik
  YARATILMAYDI bu migration orqali — faqat yangi do'konlarda
  signal ishlaydi. Mavjud do'konlar uchun data migration emas,
  chunki loyiha hali production da emas.
  (Agar kerak bo'lsa: python manage.py shell orqali yaratish mumkin)
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0003_alter_branch_unique_together'),
    ]

    operations = [
        migrations.CreateModel(
            name='StoreSettings',
            fields=[
                # Asosiy maydon
                ('id', models.BigAutoField(
                    auto_created=True,
                    primary_key=True,
                    serialize=False,
                    verbose_name='ID',
                )),
                ('store', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='settings',
                    to='store.store',
                    verbose_name="Do'kon",
                )),

                # ============================================================
                # GURUH 1 — Modul flaglari
                # ============================================================
                ('subcategory_enabled', models.BooleanField(
                    default=False,
                    verbose_name='Subkategoriya moduli',
                )),
                ('sale_return_enabled', models.BooleanField(
                    default=True,
                    verbose_name='Qaytarish moduli',
                )),
                ('wastage_enabled', models.BooleanField(
                    default=True,
                    verbose_name='Isrof moduli',
                )),
                ('stock_audit_enabled', models.BooleanField(
                    default=True,
                    verbose_name='Inventarizatsiya moduli',
                )),
                ('kpi_enabled', models.BooleanField(
                    default=False,
                    verbose_name='KPI moduli',
                )),
                ('price_list_enabled', models.BooleanField(
                    default=False,
                    verbose_name="Narx ro'yxati moduli",
                )),

                # ============================================================
                # GURUH 2 — Valyuta sozlamalari
                # ============================================================
                ('default_currency', models.CharField(
                    default='UZS',
                    max_length=3,
                    verbose_name='Asosiy valyuta (UZS | USD | RUB)',
                )),
                ('show_usd_price', models.BooleanField(
                    default=False,
                    verbose_name="USD narxini ko'rsatish",
                )),
                ('show_rub_price', models.BooleanField(
                    default=False,
                    verbose_name="RUB narxini ko'rsatish",
                )),

                # ============================================================
                # GURUH 3 — To'lov sozlamalari
                # ============================================================
                ('allow_cash', models.BooleanField(
                    default=True,
                    verbose_name="Naqd to'lov",
                )),
                ('allow_card', models.BooleanField(
                    default=True,
                    verbose_name="Karta to'lov",
                )),
                ('allow_debt', models.BooleanField(
                    default=False,
                    verbose_name='Nasiya (qarz)',
                )),

                # ============================================================
                # GURUH 4 — Chegirma sozlamalari
                # ============================================================
                ('allow_discount', models.BooleanField(
                    default=True,
                    verbose_name='Chegirma berish ruxsati',
                )),
                ('max_discount_percent', models.DecimalField(
                    decimal_places=2,
                    default=0,
                    max_digits=5,
                    verbose_name='Maksimal chegirma foizi (0 = cheksiz)',
                )),

                # ============================================================
                # GURUH 5 — Chek sozlamalari
                # ============================================================
                ('receipt_header', models.TextField(
                    blank=True,
                    verbose_name='Chek yuqori matni',
                )),
                ('receipt_footer', models.TextField(
                    blank=True,
                    verbose_name='Chek pastki matni',
                )),
                ('show_store_logo', models.BooleanField(
                    default=False,
                    verbose_name="Chekda do'kon logosi",
                )),
                ('show_worker_name', models.BooleanField(
                    default=True,
                    verbose_name='Chekda kassir ismi',
                )),

                # ============================================================
                # GURUH 6 — Ombor sozlamalari
                # ============================================================
                ('low_stock_enabled', models.BooleanField(
                    default=True,
                    verbose_name='Kam qoldiq ogohlantirish',
                )),
                ('low_stock_threshold', models.PositiveIntegerField(
                    default=5,
                    verbose_name='Ogohlantirish chegarasi (dona)',
                )),

                # ============================================================
                # GURUH 7 — Smena sozlamalari
                # ============================================================
                ('shift_enabled', models.BooleanField(
                    default=False,
                    verbose_name='Smena tizimi',
                )),
                ('shifts_per_day', models.PositiveSmallIntegerField(
                    default=1,
                    verbose_name='Kunlik smena soni (1/2/3)',
                )),
                ('require_cash_count', models.BooleanField(
                    default=False,
                    verbose_name='Smena ochish/yopishda naqd hisoblash majburiy',
                )),

                # ============================================================
                # GURUH 8 — Telegram sozlamalari
                # ============================================================
                ('telegram_enabled', models.BooleanField(
                    default=False,
                    verbose_name='Telegram bildirishnomalar',
                )),
                ('telegram_chat_id', models.CharField(
                    blank=True,
                    max_length=50,
                    null=True,
                    verbose_name='Telegram chat ID',
                )),

                # ============================================================
                # GURUH 9 — Soliq / OFD
                # ============================================================
                ('tax_enabled', models.BooleanField(
                    default=False,
                    verbose_name='QQS (soliq)',
                )),
                ('tax_percent', models.DecimalField(
                    decimal_places=2,
                    default=12,
                    max_digits=5,
                    verbose_name="QQS foizi (O'zbekistonda 12%)",
                )),
                ('ofd_enabled', models.BooleanField(
                    default=False,
                    verbose_name='OFD integratsiya (v2)',
                )),
                ('ofd_token', models.CharField(
                    blank=True,
                    max_length=255,
                    null=True,
                    verbose_name='OFD token',
                )),
                ('ofd_device_id', models.CharField(
                    blank=True,
                    max_length=100,
                    null=True,
                    verbose_name='OFD qurilma ID',
                )),

                # ============================================================
                # GURUH 10 — Yetkazib beruvchi
                # ============================================================
                ('supplier_credit_enabled', models.BooleanField(
                    default=False,
                    verbose_name="Yetkazib beruvchi qarz hisobi",
                )),
            ],
            options={
                'verbose_name':        "Do'kon sozlamalari",
                'verbose_name_plural': "Do'kon sozlamalari",
            },
        ),
    ]
