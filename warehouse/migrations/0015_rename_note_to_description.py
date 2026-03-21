from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('warehouse', '0014_supplier'),
    ]
    operations = [
        migrations.RenameField(
            model_name='stockmovement',
            old_name='note',
            new_name='description',
        ),
        migrations.RenameField(
            model_name='transfer',
            old_name='note',
            new_name='description',
        ),
        migrations.RenameField(
            model_name='transferitem',
            old_name='note',
            new_name='description',
        ),
        migrations.RenameField(
            model_name='wastagerecord',
            old_name='note',
            new_name='description',
        ),
        migrations.RenameField(
            model_name='stockaudit',
            old_name='note',
            new_name='description',
        ),
        migrations.RenameField(
            model_name='supplier',
            old_name='note',
            new_name='description',
        ),
        migrations.RenameField(
            model_name='supplierpayment',
            old_name='note',
            new_name='description',
        ),
    ]
