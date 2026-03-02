# Warehouse modellarini kengaytirish:
#   - Warehouse modeli qo'shildi (alohida fizik ombor)
#   - StockMovement: branch o'rniga from_branch/to_branch/from_warehouse/to_warehouse
#   - StockMovement: 'transfer' turi qo'shildi
#   - Stock: warehouse FK qo'shildi, branch nullable qilindi, constraint qo'shildi

import django.db.models.deletion
import django.db.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accaunt', '0005_worker_permissions_replace_extra'),
        ('warehouse', '0002_alter_product_unique_together'),
    ]

    operations = [

        # ── 1. Warehouse modeli (yangi jadval) ────────────────
        migrations.CreateModel(
            name='Warehouse',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='Nomi')),
                ('address', models.CharField(blank=True, max_length=300, verbose_name='Manzili')),
                ('status', models.CharField(choices=[('active', 'Faol'), ('inactive', 'Nofaol')], default='active', max_length=10, verbose_name='Holati')),
                ('created_on', models.DateTimeField(auto_now_add=True, verbose_name='Yaratilgan vaqti')),
                ('store', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='warehouses', to='store.store', verbose_name="Do'koni")),
            ],
            options={
                'verbose_name': 'Ombor',
                'verbose_name_plural': 'Omborlar',
                'ordering': ['name'],
                'unique_together': {('store', 'name')},
            },
        ),

        # ── 2. StockMovement.movement_type — 'transfer' qo'shildi ──
        migrations.AlterField(
            model_name='stockmovement',
            name='movement_type',
            field=models.CharField(
                choices=[('in', 'Kirim'), ('out', 'Chiqim'), ('transfer', "Ko'chirish")],
                max_length=10,
                verbose_name='Harakat turi',
            ),
        ),

        # ── 3. StockMovement.branch olib tashlandi ────────────
        migrations.RemoveField(
            model_name='stockmovement',
            name='branch',
        ),

        # ── 4–7. StockMovement ga yangi FK maydonlar ──────────
        migrations.AddField(
            model_name='stockmovement',
            name='from_branch',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='movements_from',
                to='store.branch',
                verbose_name='Filialdan',
            ),
        ),
        migrations.AddField(
            model_name='stockmovement',
            name='to_branch',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='movements_to',
                to='store.branch',
                verbose_name='Filialga',
            ),
        ),
        migrations.AddField(
            model_name='stockmovement',
            name='from_warehouse',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='movements_from',
                to='warehouse.warehouse',
                verbose_name='Ombordan',
            ),
        ),
        migrations.AddField(
            model_name='stockmovement',
            name='to_warehouse',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='movements_to',
                to='warehouse.warehouse',
                verbose_name='Omborga',
            ),
        ),

        # ── 8. Stock — eski unique_together olib tashlandi ────
        migrations.AlterUniqueTogether(
            name='stock',
            unique_together=set(),
        ),

        # ── 9. Stock.branch — nullable qilindi ────────────────
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

        # ── 10. Stock.warehouse FK qo'shildi ──────────────────
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

        # ── 11. Stock — check constraint qo'shildi ────────────
        migrations.AddConstraint(
            model_name='stock',
            constraint=models.CheckConstraint(
                condition=models.Q(
                    models.Q(('branch__isnull', False), ('warehouse__isnull', True)),
                    models.Q(('branch__isnull', True), ('warehouse__isnull', False)),
                    _connector='OR',
                ),
                name='stock_exactly_one_location',
            ),
        ),

        # ── 12. Stock — yangi unique_together ─────────────────
        migrations.AlterUniqueTogether(
            name='stock',
            unique_together={('product', 'branch'), ('product', 'warehouse')},
        ),
    ]
