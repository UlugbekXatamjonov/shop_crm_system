"""
============================================================
TRADE APP — 0001_initial migration
============================================================
Yaratilgan jadvallar:
  trade_customergroup — Mijoz guruhlari
  trade_customer      — Mijozlar
  trade_sale          — Sotuvlar
  trade_saleitem      — Sotuv elementlari

Bog'liqliklar:
  store   0005_smena                      — Store, Branch, Smena
  accaunt 0005_worker_permissions_replace_extra — Worker
  warehouse 0005_currency_exchangerate    — Product
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('accaunt',   '0005_worker_permissions_replace_extra'),
        ('store',     '0005_smena'),
        ('warehouse', '0005_currency_exchangerate'),
    ]

    operations = [

        # --------------------------------------------------------
        # CustomerGroup
        # --------------------------------------------------------
        migrations.CreateModel(
            name='CustomerGroup',
            fields=[
                ('id',         models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name',       models.CharField(max_length=100, verbose_name='Guruh nomi')),
                ('discount',   models.DecimalField(decimal_places=2, default=0, max_digits=5, verbose_name='Guruh chegirmasi (%)')),
                ('created_on', models.DateTimeField(auto_now_add=True, verbose_name='Yaratilgan vaqti')),
                ('store',      models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='customer_groups',
                    to='store.store',
                    verbose_name="Do'kon",
                )),
            ],
            options={
                'verbose_name':        'Mijoz guruhi',
                'verbose_name_plural': 'Mijoz guruhlari',
                'ordering':            ['name'],
                'unique_together':     {('store', 'name')},
            },
        ),

        # --------------------------------------------------------
        # Customer
        # --------------------------------------------------------
        migrations.CreateModel(
            name='Customer',
            fields=[
                ('id',           models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name',         models.CharField(max_length=200, verbose_name='Ism-familiya')),
                ('phone',        models.CharField(blank=True, max_length=20, verbose_name='Telefon')),
                ('address',      models.CharField(blank=True, max_length=300, verbose_name='Manzil')),
                ('debt_balance', models.DecimalField(decimal_places=2, default=0, max_digits=15, verbose_name="Nasiya qoldig'i (so'm)")),
                ('status',       models.CharField(
                    choices=[('active', 'Faol'), ('inactive', 'Nofaol')],
                    default='active',
                    max_length=10,
                    verbose_name='Holat',
                )),
                ('created_on',   models.DateTimeField(auto_now_add=True, verbose_name='Yaratilgan vaqti')),
                ('group',        models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='customers',
                    to='trade.customergroup',
                    verbose_name='Mijoz guruhi',
                )),
                ('store',        models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='customers',
                    to='store.store',
                    verbose_name="Do'kon",
                )),
            ],
            options={
                'verbose_name':        'Mijoz',
                'verbose_name_plural': 'Mijozlar',
                'ordering':            ['name'],
            },
        ),

        # --------------------------------------------------------
        # Sale
        # --------------------------------------------------------
        migrations.CreateModel(
            name='Sale',
            fields=[
                ('id',              models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('payment_type',    models.CharField(
                    choices=[
                        ('cash',  'Naqd'),
                        ('card',  'Karta'),
                        ('mixed', 'Aralash (naqd + karta)'),
                        ('debt',  'Nasiya'),
                    ],
                    max_length=10,
                    verbose_name="To'lov turi",
                )),
                ('total_price',     models.DecimalField(decimal_places=2, max_digits=15, verbose_name='Jami narx (chegirmasiz)')),
                ('discount_amount', models.DecimalField(decimal_places=2, default=0, max_digits=15, verbose_name='Chegirma summasi')),
                ('paid_amount',     models.DecimalField(decimal_places=2, max_digits=15, verbose_name="To'langan summa")),
                ('debt_amount',     models.DecimalField(decimal_places=2, default=0, max_digits=15, verbose_name='Qarz summasi')),
                ('status',          models.CharField(
                    choices=[('completed', 'Yakunlangan'), ('cancelled', 'Bekor qilingan')],
                    default='completed',
                    max_length=15,
                    verbose_name='Holat',
                )),
                ('note',            models.TextField(blank=True, verbose_name='Izoh')),
                ('created_on',      models.DateTimeField(auto_now_add=True, verbose_name='Yaratilgan vaqti')),
                ('branch',          models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='sales',
                    to='store.branch',
                    verbose_name='Filial',
                )),
                ('customer',        models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='sales',
                    to='trade.customer',
                    verbose_name='Mijoz',
                )),
                ('smena',           models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='sales',
                    to='store.smena',
                    verbose_name='Smena',
                )),
                ('store',           models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='sales',
                    to='store.store',
                    verbose_name="Do'kon",
                )),
                ('worker',          models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='sales',
                    to='accaunt.worker',
                    verbose_name='Kassir',
                )),
            ],
            options={
                'verbose_name':        'Sotuv',
                'verbose_name_plural': 'Sotuvlar',
                'ordering':            ['-created_on'],
            },
        ),

        # --------------------------------------------------------
        # SaleItem
        # --------------------------------------------------------
        migrations.CreateModel(
            name='SaleItem',
            fields=[
                ('id',          models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity',    models.DecimalField(decimal_places=3, max_digits=10, verbose_name='Miqdori')),
                ('unit_price',  models.DecimalField(decimal_places=2, max_digits=15, verbose_name='Savdo narxi (savdo paytida)')),
                ('total_price', models.DecimalField(decimal_places=2, max_digits=15, verbose_name='Jami (miqdor × narx)')),
                ('product',     models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='sale_items',
                    to='warehouse.product',
                    verbose_name='Mahsulot',
                )),
                ('sale',        models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='items',
                    to='trade.sale',
                    verbose_name='Sotuv',
                )),
            ],
            options={
                'verbose_name':        'Sotuv elementi',
                'verbose_name_plural': 'Sotuv elementlari',
            },
        ),
    ]
