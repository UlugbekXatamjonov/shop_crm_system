# Migration: warehouse_warehouse jadvalidagi ortiqcha `status` ustunini o'chirish.
#
# Muammo: production DB da `warehouse_warehouse.status` ustuni mavjud —
#   oldingi muvaffaqiyatsiz migration urinishida yaratilgan.
#   Django modeli (Warehouse) da `status` maydoni yo'q, faqat `is_active` bor.
#   INSERT da status=NULL → NOT NULL constraint buziladi →
#   `IntegrityError: null value in column "status" violates not-null constraint`
#
# Yechim: `status` ustunini DROP COLUMN IF EXISTS bilan o'chiramiz.
#   Bu idempotent — ustun mavjud bo'lmasa ham xato bermaydi.
#
# Django model holati: o'zgarmaydi (model da status yo'q edi).

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('warehouse', '0010_fix_warehouse_is_active'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                ALTER TABLE warehouse_warehouse
                    DROP COLUMN IF EXISTS status;
            """,
            reverse_sql="""
                -- Reverse: status ustunini qayta qo'shish (debug uchun)
                ALTER TABLE warehouse_warehouse
                    ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'active';
            """,
        ),
    ]
