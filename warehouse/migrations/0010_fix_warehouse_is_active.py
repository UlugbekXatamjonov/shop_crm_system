# Migration: warehouse_warehouse jadvalidagi yetishmayotgan ustunlarni qo'shish.
#
# Bu migration faqat PostgreSQL production uchun kerak edi —
# oldingi muvaffaqiyatsiz deploy natijasida yetishmayotgan ustunlar.
# SQLite (local dev) da bu operatsiyalar shart emas (0006 to'g'ri yaratadi).

from django.db import migrations


def add_missing_columns(apps, schema_editor):
    """Faqat PostgreSQL da ishlaydi — SQLite da o'tkazib yuboriladi."""
    if schema_editor.connection.vendor != 'postgresql':
        return
    schema_editor.execute("""
        ALTER TABLE warehouse_warehouse
            ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE;
        ALTER TABLE warehouse_warehouse
            ADD COLUMN IF NOT EXISTS address TEXT NOT NULL DEFAULT '';
        ALTER TABLE warehouse_warehouse
            ADD COLUMN IF NOT EXISTS created_on TIMESTAMPTZ NOT NULL DEFAULT NOW();
    """)


def remove_added_columns(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return
    schema_editor.execute("""
        ALTER TABLE warehouse_warehouse DROP COLUMN IF EXISTS is_active;
        ALTER TABLE warehouse_warehouse DROP COLUMN IF EXISTS address;
        ALTER TABLE warehouse_warehouse DROP COLUMN IF EXISTS created_on;
    """)


class Migration(migrations.Migration):

    dependencies = [
        ('warehouse', '0009_remove_exchangerate_source'),
    ]

    operations = [
        migrations.RunPython(add_missing_columns, remove_added_columns),
    ]
