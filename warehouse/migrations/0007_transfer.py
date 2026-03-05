# Migration: Transfer va TransferItem modellari qo'shildi.
#
# O'zgarishlar:
#   1. Transfer modeli yaratildi
#      - from_branch    (FK Branch, nullable)
#      - from_warehouse (FK Warehouse, nullable)
#      - to_branch      (FK Branch, nullable)
#      - to_warehouse   (FK Warehouse, nullable)
#      - store          (FK Store, CASCADE)
#      - worker         (FK Worker, SET_NULL, nullable)
#      - status         (pending | confirmed | cancelled)
#      - note, confirmed_at, created_on
#      - CheckConstraint: from_branch XOR from_warehouse
#      - CheckConstraint: to_branch   XOR to_warehouse
#   2. TransferItem modeli yaratildi
#      - transfer  (FK Transfer, CASCADE)
#      - product   (FK Product, PROTECT)
#      - quantity  (Decimal 14.3)
#      - note

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accaunt', '0005_worker_permissions_replace_extra'),
        ('store',   '0003_alter_branch_unique_together'),
        ('warehouse', '0006_warehouse'),
    ]

    operations = [

        # ── 1. Transfer modeli ───────────────────────────────────────
        migrations.CreateModel(
            name='Transfer',
            fields=[
                ('id', models.BigAutoField(
                    auto_created=True, primary_key=True,
                    serialize=False, verbose_name='ID',
                )),
                ('status', models.CharField(
                    choices=[
                        ('pending',   'Kutilmoqda'),
                        ('confirmed', 'Tasdiqlangan'),
                        ('cancelled', 'Bekor qilingan'),
                    ],
                    default='pending',
                    max_length=15,
                    verbose_name='Holati',
                )),
                ('note',         models.TextField(blank=True, verbose_name='Izoh')),
                ('confirmed_at', models.DateTimeField(null=True, blank=True, verbose_name='Tasdiqlangan vaqti')),
                ('created_on',   models.DateTimeField(auto_now_add=True, verbose_name='Yaratilgan vaqti')),

                # Manbaa: from_branch XOR from_warehouse
                ('from_branch', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='transfers_out',
                    to='store.branch',
                    verbose_name='Manbaa filial',
                )),
                ('from_warehouse', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='transfers_out',
                    to='warehouse.warehouse',
                    verbose_name='Manbaa ombor',
                )),

                # Manzil: to_branch XOR to_warehouse
                ('to_branch', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='transfers_in',
                    to='store.branch',
                    verbose_name='Manzil filial',
                )),
                ('to_warehouse', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='transfers_in',
                    to='warehouse.warehouse',
                    verbose_name='Manzil ombor',
                )),

                ('store', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='transfers',
                    to='store.store',
                    verbose_name="Do'koni",
                )),
                ('worker', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='transfers',
                    to='accaunt.worker',
                    verbose_name='Hodim',
                )),
            ],
            options={
                'verbose_name':        "Ko'chirish",
                'verbose_name_plural': "Ko'chirishlar",
                'ordering':            ['-created_on'],
            },
        ),

        # ── 2. Transfer CheckConstraint: from_branch XOR from_warehouse
        migrations.AddConstraint(
            model_name='transfer',
            constraint=models.CheckConstraint(
                check=(
                    models.Q(from_branch__isnull=False, from_warehouse__isnull=True) |
                    models.Q(from_branch__isnull=True,  from_warehouse__isnull=False)
                ),
                name='transfer_from_branch_xor_warehouse',
            ),
        ),

        # ── 3. Transfer CheckConstraint: to_branch XOR to_warehouse ──
        migrations.AddConstraint(
            model_name='transfer',
            constraint=models.CheckConstraint(
                check=(
                    models.Q(to_branch__isnull=False, to_warehouse__isnull=True) |
                    models.Q(to_branch__isnull=True,  to_warehouse__isnull=False)
                ),
                name='transfer_to_branch_xor_warehouse',
            ),
        ),

        # ── 4. TransferItem modeli ───────────────────────────────────
        migrations.CreateModel(
            name='TransferItem',
            fields=[
                ('id', models.BigAutoField(
                    auto_created=True, primary_key=True,
                    serialize=False, verbose_name='ID',
                )),
                ('quantity', models.DecimalField(
                    decimal_places=3,
                    max_digits=14,
                    verbose_name='Miqdori',
                )),
                ('note', models.TextField(blank=True, verbose_name='Izoh')),
                ('transfer', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='items',
                    to='warehouse.transfer',
                    verbose_name='Transfer',
                )),
                ('product', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='transfer_items',
                    to='warehouse.product',
                    verbose_name='Mahsulot',
                )),
            ],
            options={
                'verbose_name':        'Transfer satri',
                'verbose_name_plural': 'Transfer satrlari',
                'ordering':            ['id'],
            },
        ),
    ]
