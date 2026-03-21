from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('subscription', '0002_remove_subscriptionplan_has_price_list'),
    ]
    operations = [
        migrations.RenameField(
            model_name='subscriptioninvoice',
            old_name='note',
            new_name='description',
        ),
        migrations.RenameField(
            model_name='subscriptiondowngradelog',
            old_name='note',
            new_name='description',
        ),
    ]
