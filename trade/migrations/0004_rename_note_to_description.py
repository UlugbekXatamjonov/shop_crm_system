from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('trade', '0003_salereturn'),
    ]
    operations = [
        migrations.RenameField(
            model_name='sale',
            old_name='note',
            new_name='description',
        ),
    ]
