# Migration: SaleItem ga unit_cost maydoni qo'shildi (FIFO tannarx).
#
# O'zgarishlar:
#   SaleItem.unit_cost — DecimalField (null=True, blank=True)
#     Sotuv amalga oshirilganda FIFO bo'yicha hisoblangan tannarx saqlanadi.
#     Mavjud yozuvlar uchun NULL qoladi.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('trade', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='saleitem',
            name='unit_cost',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=15,
                null=True,
                verbose_name="Tannarx (FIFO bo'yicha, sotuv paytida)",
            ),
        ),
    ]
