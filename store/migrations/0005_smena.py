"""
Migration 0005 — Smena modeli (BOSQICH 3)

O'zgarishlar:
  1. SmenaStatus choices: open | closed
  2. Smena modeli yaratildi:
     - branch (FK → store.Branch, PROTECT)
     - store  (FK → store.Store, PROTECT)
     - worker_open  (FK → accaunt.Worker, PROTECT)
     - worker_close (FK → accaunt.Worker, PROTECT, null=True)
     - start_time (DateTimeField, auto_now_add)
     - end_time   (DateTimeField, null=True)
     - status     (CharField, max_length=10, default='open')
     - cash_start (DecimalField(15,2), default=0)
     - cash_end   (DecimalField(15,2), null=True)
     - note       (TextField, blank=True)

  ⚠️ Mavjud smenalar MAVJUD EMAS — loyiha production da emas.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accaunt', '0005_worker_permissions_replace_extra'),
        ('store', '0004_storesettings'),
    ]

    operations = [
        migrations.CreateModel(
            name='Smena',
            fields=[
                # Asosiy maydon
                ('id', models.BigAutoField(
                    auto_created=True,
                    primary_key=True,
                    serialize=False,
                    verbose_name='ID',
                )),

                # ============================================================
                # FK — Filial, Do'kon, Xodimlar
                # ============================================================
                ('branch', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='smenas',
                    to='store.branch',
                    verbose_name='Filial',
                )),
                ('store', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='smenas',
                    to='store.store',
                    verbose_name="Do'kon",
                )),
                ('worker_open', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='opened_smenas',
                    to='accaunt.worker',
                    verbose_name='Smena ochgan xodim',
                )),
                ('worker_close', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='closed_smenas',
                    to='accaunt.worker',
                    verbose_name='Smena yopgan xodim',
                )),

                # ============================================================
                # Vaqt maydonlari
                # ============================================================
                ('start_time', models.DateTimeField(
                    auto_now_add=True,
                    verbose_name='Boshlanish vaqti',
                )),
                ('end_time', models.DateTimeField(
                    blank=True,
                    null=True,
                    verbose_name='Tugash vaqti',
                )),

                # ============================================================
                # Holat
                # ============================================================
                ('status', models.CharField(
                    choices=[('open', 'Ochiq'), ('closed', 'Yopiq')],
                    default='open',
                    max_length=10,
                    verbose_name='Holat',
                )),

                # ============================================================
                # Naqd hisobi
                # ============================================================
                ('cash_start', models.DecimalField(
                    decimal_places=2,
                    default=0,
                    max_digits=15,
                    verbose_name="Boshlang'ich naqd (so'm)",
                )),
                ('cash_end', models.DecimalField(
                    blank=True,
                    decimal_places=2,
                    max_digits=15,
                    null=True,
                    verbose_name="Yakuniy naqd (so'm)",
                )),

                # ============================================================
                # Izoh
                # ============================================================
                ('note', models.TextField(
                    blank=True,
                    verbose_name='Izoh',
                )),
            ],
            options={
                'verbose_name':        'Smena',
                'verbose_name_plural': 'Smenalar',
                'ordering':            ['-start_time'],
            },
        ),
    ]
