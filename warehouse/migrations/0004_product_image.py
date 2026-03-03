import django.db.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('warehouse', '0003_expand_warehouse_models'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='image',
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to='products/',
                verbose_name='Rasm',
            ),
        ),
    ]
