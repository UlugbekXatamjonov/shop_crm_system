# Migration: warehouse_warehouse jadvalidagi yetishmayotgan ustunlarni qo'shish.
#
# Muammo: migration 0006 da `CREATE TABLE IF NOT EXISTS` ishlatilgan.
# Agar jadval oldingi (muvaffaqiyatsiz) urinishda yaratilgan bo'lsa va
# `is_active` ustuni bo'lmasa — 0006 uni o'tkazib yubordi.
#
# Natija: `django.db.utils.ProgrammingError: column warehouse_warehouse.is_active does not exist`
#
# Yechim: barcha yetishmayotgan ustunlarni `ADD COLUMN IF NOT EXISTS` bilan qo'shamiz.
# Bu operatsiya idempotent — ustun allaqachon mavjud bo'lsa xato bermaydi.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('warehouse', '0009_remove_exchangerate_source'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                -- is_active ustuni (asosiy muammo)
                ALTER TABLE warehouse_warehouse
                    ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE;

                -- address ustuni (agar u ham yo'q bo'lsa)
                ALTER TABLE warehouse_warehouse
                    ADD COLUMN IF NOT EXISTS address TEXT NOT NULL DEFAULT '';

                -- created_on ustuni (agar u ham yo'q bo'lsa)
                ALTER TABLE warehouse_warehouse
                    ADD COLUMN IF NOT EXISTS created_on TIMESTAMPTZ NOT NULL DEFAULT NOW();
            """,
            reverse_sql="""
                -- Reverse: ustunlarni olib tashlash (faqat debug uchun)
                ALTER TABLE warehouse_warehouse DROP COLUMN IF EXISTS is_active;
                ALTER TABLE warehouse_warehouse DROP COLUMN IF EXISTS address;
                ALTER TABLE warehouse_warehouse DROP COLUMN IF EXISTS created_on;
            """,
        ),
    ]
