# Migration: ExchangeRate modelidan source maydoni olib tashlandi.
#
# source maydoni doim 'CBU' qiymatiga ega edi va hech qanday
# foydali ma'lumot tashimagan. Olib tashlash orqali model soddalashtirildi.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('warehouse', '0008_stockbatch'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='exchangerate',
            name='source',
        ),
    ]
