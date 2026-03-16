from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0006_storesettings_eur_cny'),
    ]

    operations = [
        migrations.AddField(
            model_name='storesettings',
            name='auto_pdf_on_smena_close',
            field=models.BooleanField(
                default=False,
                verbose_name='Smena yopilganda Z-report PDF avtomatik generatsiya',
            ),
        ),
    ]
