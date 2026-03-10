# Migration: Warehouse.is_active → Warehouse.status (ActiveStatus).
#
# O'zgarishlar:
#   1. warehouse_warehouse.status ustuni qo'shildi (VARCHAR 10, DEFAULT 'active')
#   2. Mavjud data migratsiyasi: is_active=TRUE → 'active', FALSE → 'inactive'
#   3. warehouse_warehouse.is_active ustuni o'chirildi
#
# Sabab: loyihada barcha modellarda status=ActiveStatus qoidasi qo'llaniladi,
# Warehouse modeli ham shu qoidaga mos kelishi kerak.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('warehouse', '0011_fix_warehouse_drop_status'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(

            # ── STATE OPERATIONS ─────────────────────────────────────────────
            state_operations=[

                # 1. is_active olib tashlash
                migrations.RemoveField(
                    model_name='warehouse',
                    name='is_active',
                ),

                # 2. status qo'shish
                migrations.AddField(
                    model_name='warehouse',
                    name='status',
                    field=models.CharField(
                        choices=[('active', 'Faol'), ('inactive', 'Nofaol')],
                        default='active',
                        max_length=10,
                        verbose_name='Holati',
                    ),
                ),
            ],

            # ── DATABASE OPERATIONS ──────────────────────────────────────────
            database_operations=[

                # 1. status ustunini qo'shish (default 'active' — NOT NULL uchun)
                migrations.RunSQL(
                    sql="""
                        ALTER TABLE warehouse_warehouse
                            ADD COLUMN IF NOT EXISTS status VARCHAR(10)
                                NOT NULL DEFAULT 'active';
                    """,
                    reverse_sql="""
                        ALTER TABLE warehouse_warehouse
                            DROP COLUMN IF EXISTS status;
                    """,
                ),

                # 2. Mavjud data: is_active → status
                migrations.RunSQL(
                    sql="""
                        UPDATE warehouse_warehouse
                           SET status = CASE
                               WHEN is_active = TRUE  THEN 'active'
                               WHEN is_active = FALSE THEN 'inactive'
                               ELSE 'active'
                           END
                         WHERE is_active IS NOT NULL;
                    """,
                    reverse_sql="""
                        UPDATE warehouse_warehouse
                           SET is_active = CASE
                               WHEN status = 'active' THEN TRUE
                               ELSE FALSE
                           END;
                    """,
                ),

                # 3. is_active ustunini o'chirish
                migrations.RunSQL(
                    sql="""
                        ALTER TABLE warehouse_warehouse
                            DROP COLUMN IF EXISTS is_active;
                    """,
                    reverse_sql="""
                        ALTER TABLE warehouse_warehouse
                            ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE;
                    """,
                ),

                # 4. DEFAULT ni olib tashlash (Django o'zi boshqaradi)
                migrations.RunSQL(
                    sql="""
                        ALTER TABLE warehouse_warehouse
                            ALTER COLUMN status DROP DEFAULT;
                    """,
                    reverse_sql=migrations.RunSQL.noop,
                ),
            ],
        ),
    ]
