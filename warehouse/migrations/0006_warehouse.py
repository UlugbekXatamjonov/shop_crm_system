# Migration: Warehouse modeli qo'shildi, Stock va StockMovement yangilandi.
#
# O'zgarishlar:
#   1. Warehouse modeli yaratildi (Store ga FK)
#   2. Stock.branch — nullable qilindi (null=True, blank=True)
#   3. Stock.warehouse — yangi FK (Warehouse, null=True, blank=True)
#   4. Stock.unique_together — [('product','branch'),('product','warehouse')]
#   5. Stock CheckConstraint — branch XOR warehouse (aynan bittasi to'ldirilishi shart)
#   6. StockMovement.branch — nullable qilindi
#   7. StockMovement.warehouse — yangi FK (Warehouse, null=True, blank=True)
#   8. StockMovement CheckConstraint — branch XOR warehouse
#
# Mavjud ma'lumotlar haqida:
#   Barcha mavjud Stock va StockMovement yozuvlarida branch to'ldirilgan,
#   warehouse NULL — CheckConstraint shartini qoniqtiradi.
#
# ESLATMA: 0003_expand_warehouse_models migration avval (non-empty holda) production-ga
#   deploy qilingan va warehouse_warehouse jadvali yaratilgan edi. Keyin 0003 bo'sh
#   qilib o'zgartirildi. CreateModel IF NOT EXISTS orqali idempotent qilindi.

import django.db.models.deletion
from django.db import migrations, models


def _create_warehouse_if_not_exists(apps, schema_editor):
    """warehouse_warehouse jadvali mavjud bo'lmasa yaratadi (idempotent)."""
    tables = schema_editor.connection.introspection.table_names()
    if 'warehouse_warehouse' in tables:
        return  # Jadval allaqachon mavjud — o'tkazib yuboriladi
    Warehouse = apps.get_model('warehouse', 'Warehouse')
    schema_editor.create_model(Warehouse)


def _drop_warehouse_if_exists(apps, schema_editor):
    """Rollback: jadval mavjud bo'lsa o'chiradi."""
    tables = schema_editor.connection.introspection.table_names()
    if 'warehouse_warehouse' not in tables:
        return
    Warehouse = apps.get_model('warehouse', 'Warehouse')
    schema_editor.delete_model(Warehouse)


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0003_alter_branch_unique_together'),
        ('warehouse', '0005_currency_exchangerate'),
    ]

    operations = [

        # ── 1. Warehouse modeli (idempotent — IF NOT EXISTS) ────
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name='Warehouse',
                    fields=[
                        ('id',         models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('name',       models.CharField(max_length=200, verbose_name='Nomi')),
                        ('address',    models.TextField(blank=True, verbose_name='Manzili')),
                        ('is_active',  models.BooleanField(default=True, verbose_name='Faolmi')),
                        ('created_on', models.DateTimeField(auto_now_add=True, verbose_name='Yaratilgan vaqti')),
                        ('store',      models.ForeignKey(
                            on_delete=django.db.models.deletion.CASCADE,
                            related_name='warehouses',
                            to='store.store',
                            verbose_name="Do'koni",
                        )),
                    ],
                    options={
                        'verbose_name':        'Ombor',
                        'verbose_name_plural': 'Omborlar',
                        'ordering':            ['name'],
                        'unique_together':     {('store', 'name')},
                    },
                ),
            ],
            database_operations=[
                migrations.RunPython(
                    _create_warehouse_if_not_exists,
                    _drop_warehouse_if_exists,
                ),
            ],
        ),

        # ── 2. Stock.branch → nullable ──────────────────────────
        migrations.AlterField(
            model_name='stock',
            name='branch',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='stocks',
                to='store.branch',
                verbose_name='Filial',
            ),
        ),

        # ── 3. Stock.warehouse FK qo'shildi ────────────────────
        migrations.AddField(
            model_name='stock',
            name='warehouse',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='stocks',
                to='warehouse.warehouse',
                verbose_name='Ombor',
            ),
        ),

        # ── 4. Stock.unique_together yangilandi ────────────────
        migrations.AlterUniqueTogether(
            name='stock',
            unique_together={('product', 'branch'), ('product', 'warehouse')},
        ),

        # ── 5. Stock CheckConstraint ────────────────────────────
        migrations.AddConstraint(
            model_name='stock',
            constraint=models.CheckConstraint(
                check=(
                    models.Q(branch__isnull=False, warehouse__isnull=True) |
                    models.Q(branch__isnull=True,  warehouse__isnull=False)
                ),
                name='stock_branch_xor_warehouse',
            ),
        ),

        # ── 6. StockMovement.branch → nullable ─────────────────
        migrations.AlterField(
            model_name='stockmovement',
            name='branch',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='movements',
                to='store.branch',
                verbose_name='Filial',
            ),
        ),

        # ── 7. StockMovement.warehouse FK qo'shildi ───────────
        migrations.AddField(
            model_name='stockmovement',
            name='warehouse',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='movements',
                to='warehouse.warehouse',
                verbose_name='Ombor',
            ),
        ),

        # ── 8. StockMovement CheckConstraint ───────────────────
        migrations.AddConstraint(
            model_name='stockmovement',
            constraint=models.CheckConstraint(
                check=(
                    models.Q(branch__isnull=False, warehouse__isnull=True) |
                    models.Q(branch__isnull=True,  warehouse__isnull=False)
                ),
                name='movement_branch_xor_warehouse',
            ),
        ),
    ]
