# Migration: WastageRecord va StockAudit+StockAuditItem modellari (B7 + B8).
#
# WastageRecord — isrof/chiqindi (yaratilganda StockMovement(OUT) avtomatik)
# StockAudit    — inventarizatsiya sarlavhasi (draft→confirmed→StockMovement IN|OUT)
# StockAuditItem— inventarizatsiya satri (expected vs actual)

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accaunt', '0005_worker_permissions_replace_extra'),
        ('store', '0006_storesettings_eur_cny'),
        ('warehouse', '0012_warehouse_status'),
    ]

    operations = [
        # ── WastageRecord ─────────────────────────────────────────────────────
        migrations.CreateModel(
            name='WastageRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.DecimalField(decimal_places=3, max_digits=14, verbose_name='Miqdori')),
                ('reason', models.CharField(
                    choices=[
                        ('expired', "Muddati o'tgan"),
                        ('damaged', 'Shikastlangan'),
                        ('stolen',  "O'g'irlangan"),
                        ('other',   'Boshqa'),
                    ],
                    default='other',
                    max_length=10,
                    verbose_name='Sababi',
                )),
                ('note', models.TextField(blank=True, verbose_name='Izoh')),
                ('date', models.DateField(verbose_name='Sana')),
                ('created_on', models.DateTimeField(auto_now_add=True, verbose_name='Yaratilgan vaqti')),
                ('branch', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='wastages',
                    to='store.branch',
                    verbose_name='Filial',
                )),
                ('product', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='wastages',
                    to='warehouse.product',
                    verbose_name='Mahsulot',
                )),
                ('smena', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='wastages',
                    to='store.smena',
                    verbose_name='Smena',
                )),
                ('store', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='wastages',
                    to='store.store',
                    verbose_name="Do'kon",
                )),
                ('warehouse', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='wastages',
                    to='warehouse.warehouse',
                    verbose_name='Ombor',
                )),
                ('worker', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='wastages',
                    to='accaunt.worker',
                    verbose_name='Xodim',
                )),
            ],
            options={
                'verbose_name': 'Isrof yozuvi',
                'verbose_name_plural': 'Isrof yozuvlari',
                'ordering': ['-date', '-created_on'],
            },
        ),
        migrations.AddConstraint(
            model_name='wastagerecord',
            constraint=models.CheckConstraint(
                check=(
                    models.Q(branch__isnull=False, warehouse__isnull=True) |
                    models.Q(branch__isnull=True,  warehouse__isnull=False)
                ),
                name='wastage_branch_xor_warehouse',
            ),
        ),

        # ── StockAudit ────────────────────────────────────────────────────────
        migrations.CreateModel(
            name='StockAudit',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(
                    choices=[
                        ('draft',     'Qoralama'),
                        ('confirmed', 'Tasdiqlangan'),
                        ('cancelled', 'Bekor qilingan'),
                    ],
                    default='draft',
                    max_length=10,
                    verbose_name='Holat',
                )),
                ('note', models.TextField(blank=True, verbose_name='Izoh')),
                ('created_on', models.DateTimeField(auto_now_add=True, verbose_name='Yaratilgan vaqti')),
                ('confirmed_on', models.DateTimeField(blank=True, null=True, verbose_name='Tasdiqlangan vaqti')),
                ('branch', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='audits',
                    to='store.branch',
                    verbose_name='Filial',
                )),
                ('store', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='audits',
                    to='store.store',
                    verbose_name="Do'kon",
                )),
                ('warehouse', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='audits',
                    to='warehouse.warehouse',
                    verbose_name='Ombor',
                )),
                ('worker', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='audits',
                    to='accaunt.worker',
                    verbose_name="Inventarizatsiya o'tkazdi",
                )),
            ],
            options={
                'verbose_name': 'Inventarizatsiya',
                'verbose_name_plural': 'Inventarizatsiyalar',
                'ordering': ['-created_on'],
            },
        ),
        migrations.AddConstraint(
            model_name='stockaudit',
            constraint=models.CheckConstraint(
                check=(
                    models.Q(branch__isnull=False, warehouse__isnull=True) |
                    models.Q(branch__isnull=True,  warehouse__isnull=False)
                ),
                name='audit_branch_xor_warehouse',
            ),
        ),
        migrations.AddConstraint(
            model_name='stockaudit',
            constraint=models.UniqueConstraint(
                condition=models.Q(status='draft', branch__isnull=False),
                fields=['branch', 'status'],
                name='unique_draft_audit_branch',
            ),
        ),
        migrations.AddConstraint(
            model_name='stockaudit',
            constraint=models.UniqueConstraint(
                condition=models.Q(status='draft', warehouse__isnull=False),
                fields=['warehouse', 'status'],
                name='unique_draft_audit_warehouse',
            ),
        ),

        # ── StockAuditItem ────────────────────────────────────────────────────
        migrations.CreateModel(
            name='StockAuditItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('expected_qty', models.DecimalField(decimal_places=3, max_digits=14, verbose_name='Kutilgan miqdor (tizim)')),
                ('actual_qty',   models.DecimalField(decimal_places=3, max_digits=14, verbose_name='Haqiqiy miqdor (xodim)')),
                ('audit', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='items',
                    to='warehouse.stockaudit',
                    verbose_name='Inventarizatsiya',
                )),
                ('product', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='audit_items',
                    to='warehouse.product',
                    verbose_name='Mahsulot',
                )),
            ],
            options={
                'verbose_name': 'Inventarizatsiya satri',
                'verbose_name_plural': 'Inventarizatsiya satrlari',
                'unique_together': {('audit', 'product')},
            },
        ),
    ]
