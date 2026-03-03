"""
Migration 0005 — Currency, ExchangeRate modellari va Product.price_currency

O'zgarishlar:
  1. Currency modeli yaratildi
  2. ExchangeRate modeli yaratildi
  3. Product.price_currency FK qo'shildi (null=True, ixtiyoriy)
  4. Dastlabki valyutalar seed qilinadi:
       UZS — O'zbek so'mi (asosiy, is_base=True)
       USD — Amerikan dollari
       EUR — Yevro
       RUB — Rossiya rubli
       CNY — Xitoy yuani
"""

import django.db.models.deletion
from django.db import migrations, models


# ============================================================
# SEED DATA
# ============================================================

INITIAL_CURRENCIES = [
    # (code, name, symbol, is_base)
    ('UZS', "O'zbek so'mi",     "so'm", True),
    ('USD', 'Amerikan dollari',  '$',    False),
    ('EUR', 'Yevro',             '€',    False),
    ('RUB', 'Rossiya rubli',     '₽',    False),
    ('CNY', 'Xitoy yuani',       '¥',    False),
]


def seed_currencies(apps, schema_editor):
    """Dastlabki 5 ta valyutani jadvalga qo'shish."""
    Currency = apps.get_model('warehouse', 'Currency')
    for code, name, symbol, is_base in INITIAL_CURRENCIES:
        Currency.objects.get_or_create(
            code=code,
            defaults={
                'name':    name,
                'symbol':  symbol,
                'is_base': is_base,
            },
        )


def remove_currencies(apps, schema_editor):
    """Seed valyutalarni o'chirish (reverse migration)."""
    Currency = apps.get_model('warehouse', 'Currency')
    Currency.objects.filter(
        code__in=[c[0] for c in INITIAL_CURRENCIES]
    ).delete()


# ============================================================
# MIGRATION
# ============================================================

class Migration(migrations.Migration):

    dependencies = [
        ('warehouse', '0004_subcategory'),
    ]

    operations = [
        # 1. Currency modeli
        migrations.CreateModel(
            name='Currency',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code',    models.CharField(max_length=3, unique=True, verbose_name='Kod')),
                ('name',    models.CharField(max_length=100, verbose_name='Nomi')),
                ('symbol',  models.CharField(max_length=5, verbose_name='Belgisi')),
                ('is_base', models.BooleanField(default=False, verbose_name='Asosiy valyuta')),
            ],
            options={
                'verbose_name':        'Valyuta',
                'verbose_name_plural': 'Valyutalar',
                'ordering':            ['code'],
            },
        ),

        # 2. ExchangeRate modeli
        migrations.CreateModel(
            name='ExchangeRate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rate',       models.DecimalField(decimal_places=4, max_digits=16, verbose_name='Kurs (1 xorijiy = X UZS)')),
                ('date',       models.DateField(verbose_name='Sana')),
                ('source',     models.CharField(default='CBU', max_length=50, verbose_name='Manba')),
                ('created_on', models.DateTimeField(auto_now_add=True, verbose_name='Yaratilgan vaqti')),
                ('currency', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='rates',
                    to='warehouse.currency',
                    verbose_name='Valyuta',
                )),
            ],
            options={
                'verbose_name':        'Valyuta kursi',
                'verbose_name_plural': 'Valyuta kurslari',
                'ordering':            ['-date'],
                'unique_together':     {('currency', 'date')},
            },
        ),

        # 3. Product.price_currency FK
        migrations.AddField(
            model_name='product',
            name='price_currency',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='products',
                to='warehouse.currency',
                verbose_name='Narx valyutasi',
            ),
        ),

        # 4. Seed: dastlabki valyutalar
        migrations.RunPython(
            seed_currencies,
            reverse_code=remove_currencies,
        ),
    ]
