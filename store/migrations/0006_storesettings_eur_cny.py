# Migration: StoreSettings ga EUR va CNY valyuta maydonlari qo'shildi.
#
# O'zgarishlar:
#   1. default_currency — choices qo'shildi (UZS, USD, RUB, EUR, CNY)
#   2. show_eur_price   — yangi BooleanField (EUR narxini ko'rsatish)
#   3. show_cny_price   — yangi BooleanField (CNY narxini ko'rsatish)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0005_smena'),
    ]

    operations = [

        # 1. default_currency ga choices qo'shish (DB da o'zgarmaydi)
        migrations.AlterField(
            model_name='storesettings',
            name='default_currency',
            field=models.CharField(
                choices=[
                    ('UZS', "O'zbek so'mi (UZS)"),
                    ('USD', 'Amerika dollari (USD)'),
                    ('RUB', 'Rossiya rubli (RUB)'),
                    ('EUR', 'Yevropa yevrosi (EUR)'),
                    ('CNY', 'Xitoy yuani (CNY)'),
                ],
                default='UZS',
                max_length=3,
                verbose_name='Asosiy valyuta',
            ),
        ),

        # 2. show_eur_price
        migrations.AddField(
            model_name='storesettings',
            name='show_eur_price',
            field=models.BooleanField(
                default=False,
                verbose_name="EUR narxini ko'rsatish",
            ),
        ),

        # 3. show_cny_price
        migrations.AddField(
            model_name='storesettings',
            name='show_cny_price',
            field=models.BooleanField(
                default=False,
                verbose_name="CNY narxini ko'rsatish",
            ),
        ),
    ]
