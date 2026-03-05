# Migration: StockBatch modeli qo'shildi, StockMovement yangilandi.
#
# O'zgarishlar:
#   1. StockMovement.unit_cost — yangi maydon (DecimalField, null=True, blank=True)
#      IN harakatda: xarid narxi. OUT da: FIFO bo'yicha hisoblangan o'rtacha narx.
#   2. StockBatch modeli yaratildi:
#      - batch_code   (unique, maks 30 harf): STORE-YY-MM-DD-seq
#      - product      (FK Product, PROTECT)
#      - branch       (FK Branch,    PROTECT, null=True)
#      - warehouse    (FK Warehouse, PROTECT, null=True)
#      - unit_cost    (DecimalField 15.2)
#      - qty_received (DecimalField 14.3)
#      - qty_left     (DecimalField 14.3)
#      - movement     (OneToOneField StockMovement, SET_NULL, null=True)
#      - store        (FK Store, CASCADE)
#      - received_at  (DateTimeField, auto_now_add)
#   3. CheckConstraint: batch_branch_xor_warehouse
#
# SaleItem.unit_cost — trade/migrations/0002_saleitem_unit_cost.py da alohida qo'shildi.
#
# FIFO maqsadi:
#   Har bir IN StockMovement batch yaratadi.
#   OUT/Sotuv/Transfer.confirm da eng eski batch dan boshlab qty_left kamayadi.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store',     '0003_alter_branch_unique_together'),
        ('trade',     '0002_saleitem_unit_cost'),
        ('warehouse', '0007_transfer'),
    ]

    operations = [

        # ── 1. StockMovement.unit_cost ───────────────────────────────
        migrations.AddField(
            model_name='stockmovement',
            name='unit_cost',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=15,
                null=True,
                verbose_name='Tannarx (birlik)',
            ),
        ),

        # ── 2. StockBatch modeli ─────────────────────────────────────
        migrations.CreateModel(
            name='StockBatch',
            fields=[
                ('id', models.BigAutoField(
                    auto_created=True, primary_key=True,
                    serialize=False, verbose_name='ID',
                )),
                ('batch_code', models.CharField(
                    max_length=30,
                    unique=True,
                    verbose_name='Partiya kodi',
                )),
                ('unit_cost', models.DecimalField(
                    decimal_places=2,
                    max_digits=15,
                    verbose_name='Tannarx (birlik)',
                )),
                ('qty_received', models.DecimalField(
                    decimal_places=3,
                    max_digits=14,
                    verbose_name='Qabul qilingan miqdor',
                )),
                ('qty_left', models.DecimalField(
                    decimal_places=3,
                    max_digits=14,
                    verbose_name='Qoldiq miqdor',
                )),
                ('received_at', models.DateTimeField(
                    auto_now_add=True,
                    verbose_name='Qabul vaqti',
                )),
                ('branch', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='batches',
                    to='store.branch',
                    verbose_name='Filial',
                )),
                ('movement', models.OneToOneField(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='batch',
                    to='warehouse.stockmovement',
                    verbose_name='Kirim harakati',
                )),
                ('product', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='batches',
                    to='warehouse.product',
                    verbose_name='Mahsulot',
                )),
                ('store', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='batches',
                    to='store.store',
                    verbose_name="Do'koni",
                )),
                ('warehouse', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='batches',
                    to='warehouse.warehouse',
                    verbose_name='Ombor',
                )),
            ],
            options={
                'verbose_name':        'Partiya',
                'verbose_name_plural': 'Partiyalar',
                'ordering':            ['received_at', 'id'],
            },
        ),

        # ── 3. StockBatch CheckConstraint: branch XOR warehouse ──────
        migrations.AddConstraint(
            model_name='stockbatch',
            constraint=models.CheckConstraint(
                check=(
                    models.Q(branch__isnull=False, warehouse__isnull=True) |
                    models.Q(branch__isnull=True,  warehouse__isnull=False)
                ),
                name='batch_branch_xor_warehouse',
            ),
        ),
    ]
