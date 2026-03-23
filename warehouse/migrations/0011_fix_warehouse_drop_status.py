# Migration: warehouse_warehouse jadvalidagi ortiqcha `status` ustunini o'chirish.
#
# Bu migration faqat PostgreSQL production uchun kerak edi —
# oldingi muvaffaqiyatsiz migration qoldirgan status ustunini tozalash.
# SQLite (local dev) da status ustuni yo'q, o'tkazib yuboriladi.

from django.db import migrations


def drop_status_column(apps, schema_editor):
    """Faqat PostgreSQL da ishlaydi — SQLite da o'tkazib yuboriladi."""
    if schema_editor.connection.vendor != 'postgresql':
        return
    schema_editor.execute("""
        ALTER TABLE warehouse_warehouse
            DROP COLUMN IF EXISTS status;
    """)


def restore_status_column(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return
    schema_editor.execute("""
        ALTER TABLE warehouse_warehouse
            ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'active';
    """)


class Migration(migrations.Migration):

    dependencies = [
        ('warehouse', '0010_fix_warehouse_is_active'),
    ]

    operations = [
        migrations.RunPython(drop_status_column, restore_status_column),
    ]
