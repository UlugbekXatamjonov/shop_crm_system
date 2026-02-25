"""
Migration 0004 — Schema + Data migration (xavfsiz tartib)

O'zgarishlar:
  1. AlterField Worker.status — max_length 10 → 15, yangi choices (faol/tatil/ishdan_ketgan)
  2. AlterField Worker.role   — yangi choices (owner/manager/seller)
  3. RunPython — mavjud ma'lumotlarni yangilash:
       - role='sotuvchi'  → role='seller'
       - status='deactive' → status='ishdan_ketgan'
       - extra_permissions ichidagi 'sklad' → 'ombor'

TARTIB muhim:
  AlterField status (max_length 10→15) BIRINCHI bajariladi,
  shundan keyingina RunPython 'ishdan_ketgan' (13 ta belgi) yoza oladi.
"""

from django.db import migrations, models


# ============================================================
# DATA MIGRATION FUNKSIYALARI
# ============================================================

def migrate_worker_data(apps, schema_editor):
    """
    Eski ma'lumotlarni yangi qiymatlarga o'tkazadi:
      - sotuvchi → seller
      - deactive → ishdan_ketgan
      - extra_permissions: sklad → ombor
    """
    Worker = apps.get_model('accaunt', 'Worker')

    # 1) role: 'sotuvchi' → 'seller'
    Worker.objects.filter(role='sotuvchi').update(role='seller')

    # 2) status: 'deactive' → 'ishdan_ketgan'
    Worker.objects.filter(status='deactive').update(status='ishdan_ketgan')

    # 3) extra_permissions JSONField: 'sklad' → 'ombor'
    for worker in Worker.objects.exclude(extra_permissions={}):
        ep = worker.extra_permissions or {}
        changed = False

        added = ep.get('added', [])
        if 'sklad' in added:
            ep['added'] = ['ombor' if p == 'sklad' else p for p in added]
            changed = True

        removed = ep.get('removed', [])
        if 'sklad' in removed:
            ep['removed'] = ['ombor' if p == 'sklad' else p for p in removed]
            changed = True

        if changed:
            worker.extra_permissions = ep
            worker.save(update_fields=['extra_permissions'])


def reverse_migrate_worker_data(apps, schema_editor):
    """Orqaga qaytarish (rollback) uchun."""
    Worker = apps.get_model('accaunt', 'Worker')

    Worker.objects.filter(role='seller').update(role='sotuvchi')
    Worker.objects.filter(status='ishdan_ketgan').update(status='deactive')

    for worker in Worker.objects.exclude(extra_permissions={}):
        ep = worker.extra_permissions or {}
        changed = False

        added = ep.get('added', [])
        if 'ombor' in added:
            ep['added'] = ['sklad' if p == 'ombor' else p for p in added]
            changed = True

        removed = ep.get('removed', [])
        if 'ombor' in removed:
            ep['removed'] = ['sklad' if p == 'ombor' else p for p in removed]
            changed = True

        if changed:
            worker.extra_permissions = ep
            worker.save(update_fields=['extra_permissions'])


# ============================================================
# MIGRATION
# ============================================================

class Migration(migrations.Migration):

    dependencies = [
        ('accaunt', '0003_alter_worker_branch_verbose_name'),
    ]

    operations = [
        # 1. BIRINCHI: max_length 10 → 15 (PostgreSQL uchun muhim!)
        #    Shundan keyingina 'ishdan_ketgan' (13 ta belgi) yozish xavfsiz.
        migrations.AlterField(
            model_name='worker',
            name='status',
            field=models.CharField(
                choices=[
                    ('active',        'Faol'),
                    ('tatil',         'Tatilda'),
                    ('ishdan_ketgan', 'Ishdan ketgan'),
                ],
                default='active',
                max_length=15,
                verbose_name='Holati',
            ),
        ),

        # 2. role choices yangilanadi (max_length o'zgarmaydi — 20 yetarli)
        migrations.AlterField(
            model_name='worker',
            name='role',
            field=models.CharField(
                choices=[
                    ('owner',   'Ega'),
                    ('manager', 'Menejer'),
                    ('seller',  'Sotuvchi'),
                ],
                default='seller',
                max_length=20,
                verbose_name='Roli',
            ),
        ),

        # 3. OXIRIDA: mavjud ma'lumotlarni yangilash
        migrations.RunPython(
            migrate_worker_data,
            reverse_code=reverse_migrate_worker_data,
        ),
    ]
