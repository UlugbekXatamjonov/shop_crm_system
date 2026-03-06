# Migration: Warehouse modeli qo'shildi, Stock va StockMovement yangilandi.
#
# O'zgarishlar:
#   1. Warehouse modeli yaratildi (Store ga FK)
#   2. Stock.branch — nullable qilindi (null=True, blank=True)
#   3. Stock.warehouse — yangi FK (Warehouse, null=True, blank=True)
#   4. Stock.unique_together — [('product','branch'),('product','warehouse')]
#   5. Stock CheckConstraint — branch XOR warehouse
#   6. StockMovement.branch — nullable qilindi
#   7. StockMovement.warehouse — yangi FK (Warehouse, null=True, blank=True)
#   8. StockMovement CheckConstraint — branch XOR warehouse
#
# ESLATMA (idempotentlik):
#   0003_expand_warehouse_models migration avval non-empty holda production-ga
#   deploy qilingan va ba'zi ob'ektlar (warehouse_warehouse jadvali,
#   warehouse_id kolumnlari, ba'zi constraintlar) allaqachon mavjud bo'lishi mumkin.
#   Barcha operatsiyalar SeparateDatabaseAndState + RunPython orqali "IF NOT EXISTS"
#   mantiqiga ega qilindi.

import django.db.models.deletion
from django.db import migrations, models


# ══════════════════════════════════════════════════════════════════════════════
# Helper introspection functions
# ══════════════════════════════════════════════════════════════════════════════

def _table_exists(schema_editor, table):
    return table in schema_editor.connection.introspection.table_names()


def _column_exists(schema_editor, table, column):
    with schema_editor.connection.cursor() as cursor:
        cols = schema_editor.connection.introspection.get_table_description(cursor, table)
    return any(c.name == column for c in cols)


def _unique_for_columns_exists(schema_editor, table, columns):
    """Berilgan ustunlar uchun UNIQUE index/constraint mavjudligini tekshiradi."""
    with schema_editor.connection.cursor() as cursor:
        constraints = schema_editor.connection.introspection.get_constraints(cursor, table)
    col_set = set(columns)
    return any(
        info['unique'] and set(info['columns']) == col_set
        for info in constraints.values()
    )


def _named_constraint_exists(schema_editor, constraint_name):
    """pg_constraint ichida nom bo'yicha constraint mavjudligini tekshiradi."""
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            "SELECT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = %s)",
            [constraint_name],
        )
        return cursor.fetchone()[0]


# ══════════════════════════════════════════════════════════════════════════════
# 1. Warehouse modeli
# ══════════════════════════════════════════════════════════════════════════════

def _create_warehouse_if_not_exists(apps, schema_editor):
    if _table_exists(schema_editor, 'warehouse_warehouse'):
        return
    Warehouse = apps.get_model('warehouse', 'Warehouse')
    schema_editor.create_model(Warehouse)


def _drop_warehouse_if_exists(apps, schema_editor):
    if not _table_exists(schema_editor, 'warehouse_warehouse'):
        return
    Warehouse = apps.get_model('warehouse', 'Warehouse')
    schema_editor.delete_model(Warehouse)


# ══════════════════════════════════════════════════════════════════════════════
# 3. Stock.warehouse FK
# ══════════════════════════════════════════════════════════════════════════════

def _add_stock_warehouse_if_not_exists(apps, schema_editor):
    if _column_exists(schema_editor, 'warehouse_stock', 'warehouse_id'):
        return
    Stock = apps.get_model('warehouse', 'Stock')
    schema_editor.add_field(Stock, Stock._meta.get_field('warehouse'))


def _remove_stock_warehouse_if_exists(apps, schema_editor):
    if not _column_exists(schema_editor, 'warehouse_stock', 'warehouse_id'):
        return
    Stock = apps.get_model('warehouse', 'Stock')
    schema_editor.remove_field(Stock, Stock._meta.get_field('warehouse'))


# ══════════════════════════════════════════════════════════════════════════════
# 4. Stock unique_together: ('product', 'warehouse') qo'shiladi
# ══════════════════════════════════════════════════════════════════════════════

def _add_stock_warehouse_unique_if_not_exists(apps, schema_editor):
    if _unique_for_columns_exists(schema_editor, 'warehouse_stock', ['product_id', 'warehouse_id']):
        return
    Stock = apps.get_model('warehouse', 'Stock')
    # Faqat ('product','warehouse') qo'shiladi; ('product','branch') tegilmaydi
    schema_editor.alter_unique_together(Stock, set(), {('product', 'warehouse')})


def _remove_stock_warehouse_unique_if_exists(apps, schema_editor):
    if not _unique_for_columns_exists(schema_editor, 'warehouse_stock', ['product_id', 'warehouse_id']):
        return
    Stock = apps.get_model('warehouse', 'Stock')
    schema_editor.alter_unique_together(Stock, {('product', 'warehouse')}, set())


# ══════════════════════════════════════════════════════════════════════════════
# 5. Stock CheckConstraint: stock_branch_xor_warehouse
# ══════════════════════════════════════════════════════════════════════════════

_STOCK_CHECK = models.CheckConstraint(
    check=(
        models.Q(branch__isnull=False, warehouse__isnull=True) |
        models.Q(branch__isnull=True,  warehouse__isnull=False)
    ),
    name='stock_branch_xor_warehouse',
)


def _add_stock_check_if_not_exists(apps, schema_editor):
    if _named_constraint_exists(schema_editor, 'stock_branch_xor_warehouse'):
        return
    Stock = apps.get_model('warehouse', 'Stock')
    schema_editor.add_constraint(Stock, _STOCK_CHECK)


def _remove_stock_check_if_exists(apps, schema_editor):
    if not _named_constraint_exists(schema_editor, 'stock_branch_xor_warehouse'):
        return
    Stock = apps.get_model('warehouse', 'Stock')
    schema_editor.remove_constraint(Stock, _STOCK_CHECK)


# ══════════════════════════════════════════════════════════════════════════════
# 7. StockMovement.warehouse FK
# ══════════════════════════════════════════════════════════════════════════════

def _add_movement_warehouse_if_not_exists(apps, schema_editor):
    if _column_exists(schema_editor, 'warehouse_stockmovement', 'warehouse_id'):
        return
    StockMovement = apps.get_model('warehouse', 'StockMovement')
    schema_editor.add_field(StockMovement, StockMovement._meta.get_field('warehouse'))


def _remove_movement_warehouse_if_exists(apps, schema_editor):
    if not _column_exists(schema_editor, 'warehouse_stockmovement', 'warehouse_id'):
        return
    StockMovement = apps.get_model('warehouse', 'StockMovement')
    schema_editor.remove_field(StockMovement, StockMovement._meta.get_field('warehouse'))


# ══════════════════════════════════════════════════════════════════════════════
# 8. StockMovement CheckConstraint: movement_branch_xor_warehouse
# ══════════════════════════════════════════════════════════════════════════════

_MOVEMENT_CHECK = models.CheckConstraint(
    check=(
        models.Q(branch__isnull=False, warehouse__isnull=True) |
        models.Q(branch__isnull=True,  warehouse__isnull=False)
    ),
    name='movement_branch_xor_warehouse',
)


def _add_movement_check_if_not_exists(apps, schema_editor):
    if _named_constraint_exists(schema_editor, 'movement_branch_xor_warehouse'):
        return
    StockMovement = apps.get_model('warehouse', 'StockMovement')
    schema_editor.add_constraint(StockMovement, _MOVEMENT_CHECK)


def _remove_movement_check_if_exists(apps, schema_editor):
    if not _named_constraint_exists(schema_editor, 'movement_branch_xor_warehouse'):
        return
    StockMovement = apps.get_model('warehouse', 'StockMovement')
    schema_editor.remove_constraint(StockMovement, _MOVEMENT_CHECK)


# ══════════════════════════════════════════════════════════════════════════════
# Migration class
# ══════════════════════════════════════════════════════════════════════════════

class Migration(migrations.Migration):

    dependencies = [
        ('store', '0003_alter_branch_unique_together'),
        ('warehouse', '0005_currency_exchangerate'),
    ]

    operations = [

        # ── 1. Warehouse modeli (idempotent: IF NOT EXISTS) ─────────────────
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
                migrations.RunPython(_create_warehouse_if_not_exists, _drop_warehouse_if_exists),
            ],
        ),

        # ── 2. Stock.branch → nullable (PG-da idempotent) ──────────────────
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

        # ── 3. Stock.warehouse FK (idempotent: column IF NOT EXISTS) ────────
        migrations.SeparateDatabaseAndState(
            state_operations=[
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
            ],
            database_operations=[
                migrations.RunPython(_add_stock_warehouse_if_not_exists, _remove_stock_warehouse_if_exists),
            ],
        ),

        # ── 4. Stock.unique_together yangilandi (idempotent) ────────────────
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterUniqueTogether(
                    name='stock',
                    unique_together={('product', 'branch'), ('product', 'warehouse')},
                ),
            ],
            database_operations=[
                migrations.RunPython(
                    _add_stock_warehouse_unique_if_not_exists,
                    _remove_stock_warehouse_unique_if_exists,
                ),
            ],
        ),

        # ── 5. Stock CheckConstraint (idempotent) ───────────────────────────
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddConstraint(
                    model_name='stock',
                    constraint=_STOCK_CHECK,
                ),
            ],
            database_operations=[
                migrations.RunPython(_add_stock_check_if_not_exists, _remove_stock_check_if_exists),
            ],
        ),

        # ── 6. StockMovement.branch → nullable (PG-da idempotent) ──────────
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

        # ── 7. StockMovement.warehouse FK (idempotent) ──────────────────────
        migrations.SeparateDatabaseAndState(
            state_operations=[
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
            ],
            database_operations=[
                migrations.RunPython(_add_movement_warehouse_if_not_exists, _remove_movement_warehouse_if_exists),
            ],
        ),

        # ── 8. StockMovement CheckConstraint (idempotent) ───────────────────
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddConstraint(
                    model_name='stockmovement',
                    constraint=_MOVEMENT_CHECK,
                ),
            ],
            database_operations=[
                migrations.RunPython(_add_movement_check_if_not_exists, _remove_movement_check_if_exists),
            ],
        ),
    ]
