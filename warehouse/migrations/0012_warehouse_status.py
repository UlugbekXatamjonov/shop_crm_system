# Migration: Warehouse.is_active → Warehouse.status (ActiveStatus).
#
# O'zgarishlar:
#   1. warehouse_warehouse.status ustuni qo'shildi (VARCHAR 10, DEFAULT 'active')
#   2. Mavjud data migratsiyasi: is_active=TRUE → 'active', FALSE → 'inactive'
#   3. warehouse_warehouse.is_active ustuni o'chirildi
#
# SQLite va PostgreSQL da ishlaydi.
# Production da bu migration allaqachon applied — qayta ishlamaydi.

import django.db.models.deletion
from django.db import migrations, models


def migrate_data(apps, schema_editor):
    """is_active → status ma'lumot ko'chirish (mavjud yozuvlar uchun)."""
    Warehouse = apps.get_model('warehouse', 'Warehouse')
    Warehouse.objects.filter(is_active=True).update(status='active')
    Warehouse.objects.filter(is_active=False).update(status='inactive')


class Migration(migrations.Migration):

    dependencies = [
        ('warehouse', '0011_fix_warehouse_drop_status'),
    ]

    operations = [

        # 1. status ustuni qo'shish (default='active' — NOT NULL uchun)
        migrations.AddField(
            model_name='warehouse',
            name='status',
            field=models.CharField(
                choices=[('active', 'Faol'), ('inactive', 'Nofaol')],
                default='active',
                max_length=10,
                verbose_name='Holati',
            ),
            preserve_default=False,
        ),

        # 2. Mavjud data ko'chirish
        migrations.RunPython(migrate_data, migrations.RunPython.noop),

        # 3. is_active ustunini o'chirish
        migrations.RemoveField(
            model_name='warehouse',
            name='is_active',
        ),
    ]
