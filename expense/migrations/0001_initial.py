# Migration: ExpenseCategory va Expense modellari (BOSQICH 6).

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('accaunt', '0005_worker_permissions_replace_extra'),
        ('store', '0006_storesettings_eur_cny'),
        ('warehouse', '0008_stockbatch'),
    ]

    operations = [
        migrations.CreateModel(
            name='ExpenseCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='Nomi')),
                ('status', models.CharField(
                    choices=[('active', 'Faol'), ('inactive', 'Nofaol')],
                    default='active',
                    max_length=10,
                    verbose_name='Holat',
                )),
                ('created_on', models.DateTimeField(auto_now_add=True, verbose_name='Yaratilgan vaqti')),
                ('store', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='expense_categories',
                    to='store.store',
                    verbose_name="Do'kon",
                )),
            ],
            options={
                'verbose_name': 'Xarajat kategoriyasi',
                'verbose_name_plural': 'Xarajat kategoriyalari',
                'ordering': ['name'],
                'unique_together': {('store', 'name')},
            },
        ),
        migrations.CreateModel(
            name='Expense',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=15, verbose_name="Summa (so'm)")),
                ('description', models.TextField(blank=True, verbose_name='Izoh')),
                ('date', models.DateField(verbose_name='Sana')),
                ('receipt_image', models.ImageField(blank=True, null=True, upload_to='expenses/', verbose_name='Kvitansiya rasmi')),
                ('created_on', models.DateTimeField(auto_now_add=True, verbose_name='Yaratilgan vaqti')),
                ('branch', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='expenses',
                    to='store.branch',
                    verbose_name='Filial',
                )),
                ('category', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='expenses',
                    to='expense.expensecategory',
                    verbose_name='Kategoriya',
                )),
                ('smena', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='expenses',
                    to='store.smena',
                    verbose_name='Smena',
                )),
                ('store', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='expenses',
                    to='store.store',
                    verbose_name="Do'kon",
                )),
                ('worker', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='expenses',
                    to='accaunt.worker',
                    verbose_name='Xodim',
                )),
            ],
            options={
                'verbose_name': 'Xarajat',
                'verbose_name_plural': 'Xarajatlar',
                'ordering': ['-date', '-created_on'],
            },
        ),
    ]
