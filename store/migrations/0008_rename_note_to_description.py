from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('store', '0007_storesettings_auto_pdf'),
    ]
    operations = [
        migrations.RenameField(
            model_name='smena',
            old_name='note',
            new_name='description',
        ),
    ]
