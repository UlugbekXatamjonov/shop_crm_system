# Migration: WorkerKPI modeli (B9 — xodim oylik KPI ko'rsatkichlari).
#
# WorkerKPI — har bir xodim uchun oylik savdo ko'rsatkichlari:
#   sales_count, sales_amount, returns_count, returns_amount
#   target_amount, bonus_amount (manager belgilaydi)
#   unique_together: (worker, month, year)

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accaunt', '0005_worker_permissions_replace_extra'),
        ('store',   '0006_storesettings_eur_cny'),
    ]

    operations = [
        migrations.CreateModel(
            name='WorkerKPI',
            fields=[
                ('id', models.BigAutoField(
                    auto_created=True, primary_key=True,
                    serialize=False, verbose_name='ID',
                )),
                ('month', models.PositiveSmallIntegerField(
                    verbose_name='Oy (1-12)',
                )),
                ('year', models.PositiveSmallIntegerField(
                    verbose_name='Yil',
                )),
                ('sales_count', models.PositiveIntegerField(
                    default=0,
                    verbose_name='Sotuvlar soni',
                )),
                ('sales_amount', models.DecimalField(
                    decimal_places=2, default=0, max_digits=15,
                    verbose_name='Sotuvlar summasi (chegirma keyin)',
                )),
                ('returns_count', models.PositiveIntegerField(
                    default=0,
                    verbose_name='Qaytarishlar soni',
                )),
                ('returns_amount', models.DecimalField(
                    decimal_places=2, default=0, max_digits=15,
                    verbose_name='Qaytarishlar summasi',
                )),
                ('target_amount', models.DecimalField(
                    decimal_places=2, default=0, max_digits=15,
                    verbose_name='Oylik maqsad (manager belgilaydi)',
                )),
                ('bonus_amount', models.DecimalField(
                    decimal_places=2, default=0, max_digits=15,
                    verbose_name='Bonus summasi (maqsad bajarilsa)',
                )),
                ('store', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='kpi_records',
                    to='store.store',
                    verbose_name="Do'kon",
                )),
                ('worker', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='kpi_records',
                    to='accaunt.worker',
                    verbose_name='Xodim',
                )),
            ],
            options={
                'verbose_name':        'Xodim KPI',
                'verbose_name_plural': 'Xodim KPI lar',
                'ordering':            ['-year', '-month'],
            },
        ),
        migrations.AlterUniqueTogether(
            name='workerkpi',
            unique_together={('worker', 'month', 'year')},
        ),
    ]
