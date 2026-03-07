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
# Eslatma: SeparateDatabaseAndState ishlatilgan — database_operations da
# PostgreSQL IF NOT EXISTS sintaksisi bilan idempotent DDL yozilgan.
# Sabab: oldingi muvaffaqiyatsiz deploy urinishlari natijasida
# warehouse_warehouse jadvali allaqachon mavjud bo'lishi mumkin.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0003_alter_branch_unique_together'),
        ('warehouse', '0005_currency_exchangerate'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(

            # ────────────────────────────────────────────────────────────────
            # STATE OPERATIONS — faqat Django ichki model holati (DB ga ta'sir
            # qilmaydi); keyingi migration'lar uchun to'g'ri state kerak.
            # ────────────────────────────────────────────────────────────────
            state_operations=[

                # 1. Warehouse modeli
                migrations.CreateModel(
                    name='Warehouse',
                    fields=[
                        ('id', models.BigAutoField(
                            auto_created=True, primary_key=True,
                            serialize=False, verbose_name='ID',
                        )),
                        ('name', models.CharField(max_length=200, verbose_name='Nomi')),
                        ('address', models.TextField(blank=True, verbose_name='Manzili')),
                        ('is_active', models.BooleanField(default=True, verbose_name='Faolmi')),
                        ('created_on', models.DateTimeField(
                            auto_now_add=True, verbose_name='Yaratilgan vaqti',
                        )),
                        ('store', models.ForeignKey(
                            on_delete=django.db.models.deletion.CASCADE,
                            related_name='warehouses',
                            to='store.store',
                            verbose_name="Do'koni",
                        )),
                    ],
                    options={
                        'verbose_name': 'Ombor',
                        'verbose_name_plural': 'Omborlar',
                        'ordering': ['name'],
                        'unique_together': {('store', 'name')},
                    },
                ),

                # 2. Stock.branch → nullable
                migrations.AlterField(
                    model_name='stock',
                    name='branch',
                    field=models.ForeignKey(
                        blank=True, null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='stocks',
                        to='store.branch',
                        verbose_name='Filial',
                    ),
                ),

                # 3. Stock.warehouse FK
                migrations.AddField(
                    model_name='stock',
                    name='warehouse',
                    field=models.ForeignKey(
                        blank=True, null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='stocks',
                        to='warehouse.warehouse',
                        verbose_name='Ombor',
                    ),
                ),

                # 4. Stock unique_together
                migrations.AlterUniqueTogether(
                    name='stock',
                    unique_together={('product', 'branch'), ('product', 'warehouse')},
                ),

                # 5. Stock XOR constraint
                migrations.AddConstraint(
                    model_name='stock',
                    constraint=models.CheckConstraint(
                        check=(
                            models.Q(branch__isnull=False, warehouse__isnull=True)
                            | models.Q(branch__isnull=True, warehouse__isnull=False)
                        ),
                        name='stock_branch_xor_warehouse',
                    ),
                ),

                # 6. StockMovement.branch → nullable
                migrations.AlterField(
                    model_name='stockmovement',
                    name='branch',
                    field=models.ForeignKey(
                        blank=True, null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='movements',
                        to='store.branch',
                        verbose_name='Filial',
                    ),
                ),

                # 7. StockMovement.warehouse FK
                migrations.AddField(
                    model_name='stockmovement',
                    name='warehouse',
                    field=models.ForeignKey(
                        blank=True, null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='movements',
                        to='warehouse.warehouse',
                        verbose_name='Ombor',
                    ),
                ),

                # 8. StockMovement XOR constraint
                migrations.AddConstraint(
                    model_name='stockmovement',
                    constraint=models.CheckConstraint(
                        check=(
                            models.Q(branch__isnull=False, warehouse__isnull=True)
                            | models.Q(branch__isnull=True, warehouse__isnull=False)
                        ),
                        name='movement_branch_xor_warehouse',
                    ),
                ),
            ],

            # ────────────────────────────────────────────────────────────────
            # DATABASE OPERATIONS — haqiqiy DDL, idempotent (IF NOT EXISTS).
            # PostgreSQL 9.5+ da ishlaydi (Railway PostgreSQL 14/15/16).
            # ────────────────────────────────────────────────────────────────
            database_operations=[

                # 1. Ombor jadvali (mavjud bo'lsa o'tkazib yuborish)
                migrations.RunSQL(
                    sql="""
                        CREATE TABLE IF NOT EXISTS warehouse_warehouse (
                            id         BIGSERIAL    PRIMARY KEY,
                            name       VARCHAR(200) NOT NULL,
                            address    TEXT         NOT NULL DEFAULT '',
                            is_active  BOOLEAN      NOT NULL DEFAULT TRUE,
                            created_on TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
                            store_id   BIGINT       NOT NULL
                                       REFERENCES store_store(id) ON DELETE CASCADE
                        );
                        CREATE UNIQUE INDEX IF NOT EXISTS
                            warehouse_warehouse_store_id_name_uniq
                            ON warehouse_warehouse(store_id, name);
                    """,
                    reverse_sql="""
                        DROP INDEX IF EXISTS warehouse_warehouse_store_id_name_uniq;
                        DROP TABLE IF EXISTS warehouse_warehouse CASCADE;
                    """,
                ),

                # 2. Stock.branch_id → nullable
                migrations.RunSQL(
                    sql="ALTER TABLE warehouse_stock ALTER COLUMN branch_id DROP NOT NULL;",
                    reverse_sql="ALTER TABLE warehouse_stock ALTER COLUMN branch_id SET NOT NULL;",
                ),

                # 3. Stock.warehouse_id FK ustuni (mavjud bo'lsa o'tkazib yuborish)
                migrations.RunSQL(
                    sql="""
                        ALTER TABLE warehouse_stock
                            ADD COLUMN IF NOT EXISTS warehouse_id BIGINT
                                REFERENCES warehouse_warehouse(id) ON DELETE CASCADE;
                    """,
                    reverse_sql="""
                        ALTER TABLE warehouse_stock DROP COLUMN IF EXISTS warehouse_id;
                    """,
                ),

                # 4. Stock: (product_id, warehouse_id) UNIQUE indeks
                migrations.RunSQL(
                    sql="""
                        CREATE UNIQUE INDEX IF NOT EXISTS
                            warehouse_stock_product_id_warehouse_id_uniq
                            ON warehouse_stock(product_id, warehouse_id);
                    """,
                    reverse_sql="""
                        DROP INDEX IF EXISTS warehouse_stock_product_id_warehouse_id_uniq;
                    """,
                ),

                # 5. Stock XOR CHECK constrainti (mavjud bo'lsa o'tkazib yuborish)
                migrations.RunSQL(
                    sql="""
                        DO $$
                        BEGIN
                            IF NOT EXISTS (
                                SELECT 1 FROM pg_constraint
                                 WHERE conrelid = 'warehouse_stock'::regclass
                                   AND conname  = 'stock_branch_xor_warehouse'
                            ) THEN
                                ALTER TABLE warehouse_stock
                                    ADD CONSTRAINT stock_branch_xor_warehouse CHECK (
                                        (branch_id IS NOT NULL AND warehouse_id IS NULL) OR
                                        (branch_id IS NULL     AND warehouse_id IS NOT NULL)
                                    );
                            END IF;
                        END $$;
                    """,
                    reverse_sql="""
                        ALTER TABLE warehouse_stock
                            DROP CONSTRAINT IF EXISTS stock_branch_xor_warehouse;
                    """,
                ),

                # 6. StockMovement.branch_id → nullable
                migrations.RunSQL(
                    sql="ALTER TABLE warehouse_stockmovement ALTER COLUMN branch_id DROP NOT NULL;",
                    reverse_sql="ALTER TABLE warehouse_stockmovement ALTER COLUMN branch_id SET NOT NULL;",
                ),

                # 7. StockMovement.warehouse_id FK ustuni (mavjud bo'lsa o'tkazib yuborish)
                migrations.RunSQL(
                    sql="""
                        ALTER TABLE warehouse_stockmovement
                            ADD COLUMN IF NOT EXISTS warehouse_id BIGINT
                                REFERENCES warehouse_warehouse(id) ON DELETE CASCADE;
                    """,
                    reverse_sql="""
                        ALTER TABLE warehouse_stockmovement
                            DROP COLUMN IF EXISTS warehouse_id;
                    """,
                ),

                # 8. StockMovement XOR CHECK constrainti (mavjud bo'lsa o'tkazib yuborish)
                migrations.RunSQL(
                    sql="""
                        DO $$
                        BEGIN
                            IF NOT EXISTS (
                                SELECT 1 FROM pg_constraint
                                 WHERE conrelid = 'warehouse_stockmovement'::regclass
                                   AND conname  = 'movement_branch_xor_warehouse'
                            ) THEN
                                ALTER TABLE warehouse_stockmovement
                                    ADD CONSTRAINT movement_branch_xor_warehouse CHECK (
                                        (branch_id IS NOT NULL AND warehouse_id IS NULL) OR
                                        (branch_id IS NULL     AND warehouse_id IS NOT NULL)
                                    );
                            END IF;
                        END $$;
                    """,
                    reverse_sql="""
                        ALTER TABLE warehouse_stockmovement
                            DROP CONSTRAINT IF EXISTS movement_branch_xor_warehouse;
                    """,
                ),
            ],
        ),
    ]
