"""
Migration 0004 — SubCategory modeli va Product yangilanishlari

O'zgarishlar:
  1. SubCategory modeli yaratildi (Category → SubCategory → Product ierarxiyasi)
  2. Product.subcategory FK qo'shildi (null=True, ixtiyoriy)
  3. Product.unit — 'quti' varianti qo'shildi
  4. Product.purchase_price verbose_name yangilandi (UZS qisqa qilindi)
  5. Product.sale_price verbose_name yangilandi (UZS qisqa qilindi)
  6. Product.barcode verbose_name yangilandi (EAN-13 qo'shildi)
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0002_alter_branch_options_alter_store_options_and_more'),
        ('warehouse', '0003_product_image'),
    ]

    operations = [
        # 1. SubCategory modeli
        migrations.CreateModel(
            name='SubCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='Nomi')),
                ('description', models.TextField(blank=True, verbose_name='Tavsifi')),
                ('status', models.CharField(
                    choices=[('active', 'Faol'), ('inactive', 'Nofaol')],
                    default='active',
                    max_length=10,
                    verbose_name='Holati',
                )),
                ('created_on', models.DateTimeField(auto_now_add=True, verbose_name='Yaratilgan vaqti')),
                ('category', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='subcategories',
                    to='warehouse.category',
                    verbose_name='Kategoriyasi',
                )),
                ('store', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='subcategories',
                    to='store.store',
                    verbose_name="Do'koni",
                )),
            ],
            options={
                'verbose_name': 'Subkategoriya',
                'verbose_name_plural': 'Subkategoriyalar',
                'ordering': ['name'],
                'unique_together': {('store', 'category', 'name')},
            },
        ),

        # 2. Product.subcategory FK
        migrations.AddField(
            model_name='product',
            name='subcategory',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='products',
                to='warehouse.subcategory',
                verbose_name='Subkategoriyasi',
            ),
        ),

        # 3. Product.unit — 'quti' varianti qo'shildi
        migrations.AlterField(
            model_name='product',
            name='unit',
            field=models.CharField(
                choices=[
                    ('dona',   'Dona'),
                    ('kg',     'Kilogram'),
                    ('g',      'Gram'),
                    ('litr',   'Litr'),
                    ('metr',   'Metr'),
                    ('m2',     'Kvadrat metr'),
                    ('yashik', 'Yashik'),
                    ('qop',    'Qop'),
                    ('quti',   'Quti'),
                ],
                default='dona',
                max_length=10,
                verbose_name="O'lchov birligi",
            ),
        ),

        # 4. Product.purchase_price verbose_name
        migrations.AlterField(
            model_name='product',
            name='purchase_price',
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                max_digits=14,
                verbose_name='Xarid narxi',
            ),
        ),

        # 5. Product.sale_price verbose_name
        migrations.AlterField(
            model_name='product',
            name='sale_price',
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                max_digits=14,
                verbose_name='Sotish narxi',
            ),
        ),

        # 6. Product.barcode verbose_name (EAN-13 qo'shildi)
        migrations.AlterField(
            model_name='product',
            name='barcode',
            field=models.CharField(
                blank=True,
                max_length=100,
                null=True,
                verbose_name='Shtrix-kod (EAN-13)',
            ),
        ),
    ]
