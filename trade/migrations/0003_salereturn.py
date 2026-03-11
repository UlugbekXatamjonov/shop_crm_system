# Migration: SaleReturn va SaleReturnItem modellari qo'shildi (BOSQICH 5).
#
# O'zgarishlar:
#   SaleReturn — qaytarish yozuvi (pending→confirmed→StockMovement(IN))
#   SaleReturnItem — qaytarish elementi (mahsulot, miqdor, narx)

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accaunt', '0005_worker_permissions_replace_extra'),
        ('store', '0006_storesettings_eur_cny'),
        ('trade', '0002_saleitem_unit_cost'),
        ('warehouse', '0008_stockbatch'),
    ]

    operations = [
        migrations.CreateModel(
            name='SaleReturn',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reason', models.TextField(blank=True, verbose_name='Qaytarish sababi')),
                ('total_amount', models.DecimalField(decimal_places=2, default=0, max_digits=15, verbose_name='Jami qaytarilgan summa')),
                ('status', models.CharField(
                    choices=[('pending', 'Kutilmoqda'), ('confirmed', 'Tasdiqlangan'), ('cancelled', 'Bekor qilingan')],
                    default='pending',
                    max_length=10,
                    verbose_name='Holat',
                )),
                ('created_on', models.DateTimeField(auto_now_add=True, verbose_name='Yaratilgan vaqti')),
                ('branch', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='sale_returns',
                    to='store.branch',
                    verbose_name='Filial',
                )),
                ('customer', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='sale_returns',
                    to='trade.customer',
                    verbose_name='Mijoz',
                )),
                ('sale', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='returns',
                    to='trade.sale',
                    verbose_name='Asl sotuv',
                )),
                ('smena', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='sale_returns',
                    to='store.smena',
                    verbose_name='Smena',
                )),
                ('store', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='sale_returns',
                    to='store.store',
                    verbose_name="Do'kon",
                )),
                ('worker', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='sale_returns',
                    to='accaunt.worker',
                    verbose_name='Xodim',
                )),
            ],
            options={
                'verbose_name': 'Qaytarish',
                'verbose_name_plural': 'Qaytarishlar',
                'ordering': ['-created_on'],
            },
        ),
        migrations.CreateModel(
            name='SaleReturnItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.DecimalField(decimal_places=3, max_digits=10, verbose_name='Miqdori')),
                ('unit_price', models.DecimalField(decimal_places=2, max_digits=15, verbose_name='Birlik narxi')),
                ('total_price', models.DecimalField(decimal_places=2, max_digits=15, verbose_name='Jami (miqdor × narx)')),
                ('product', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='return_items',
                    to='warehouse.product',
                    verbose_name='Mahsulot',
                )),
                ('sale_return', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='items',
                    to='trade.salereturn',
                    verbose_name='Qaytarish',
                )),
            ],
            options={
                'verbose_name': 'Qaytarish elementi',
                'verbose_name_plural': 'Qaytarish elementlari',
            },
        ),
    ]
