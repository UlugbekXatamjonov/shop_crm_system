"""
Migration 0005 — extra_permissions → permissions

O'zgarishlar:
  1. AddField  : Worker.permissions (JSONField, default=list)
  2. RunPython : Mavjud extra_permissions dan haqiqiy ruxsatlarni hisoblab to'ldiradi
  3. RemoveField: Worker.extra_permissions o'chiriladi

Teskari migratsiya (reverse):
  1. AddField  : Worker.extra_permissions (JSONField, default=dict)
  2. RunPython : permissions dan extra_permissions formatiga qaytaradi
  3. RemoveField: Worker.permissions o'chiriladi
"""

from django.db import migrations, models


# ============================================================
# DATA MIGRATION FUNKSIYALARI
# ============================================================

def migrate_to_permissions(apps, schema_editor):
    """
    extra_permissions (added/removed) dan haqiqiy permissions ro'yxatini hisoblaydi.

    Mantiq:
      permissions = sorted((ROLE_DEFAULT + added) - removed)
    """
    Worker = apps.get_model('accaunt', 'Worker')

    ROLE_DEFAULTS = {
        'owner':   ['boshqaruv', 'sotuv', 'dokonlar', 'ombor',
                    'mahsulotlar', 'xodimlar', 'savdolar',
                    'xarajatlar', 'mijozlar', 'sozlamalar'],
        'manager': ['boshqaruv', 'sotuv', 'dokonlar', 'ombor',
                    'mahsulotlar', 'xodimlar', 'savdolar',
                    'xarajatlar', 'mijozlar'],
        'seller':  ['sotuv', 'savdolar', 'mijozlar', 'ombor', 'mahsulotlar'],
    }

    for worker in Worker.objects.all():
        extra   = worker.extra_permissions or {}
        base    = set(ROLE_DEFAULTS.get(worker.role, []))
        added   = set(extra.get('added',   []))
        removed = set(extra.get('removed', []))
        worker.permissions = sorted((base | added) - removed)
        worker.save(update_fields=['permissions'])


def reverse_to_extra_permissions(apps, schema_editor):
    """
    permissions ro'yxatidan extra_permissions formatiga qaytaradi.

    Mantiq:
      added   = permissions - ROLE_DEFAULT
      removed = ROLE_DEFAULT - permissions
    """
    Worker = apps.get_model('accaunt', 'Worker')

    ROLE_DEFAULTS = {
        'owner':   set(['boshqaruv', 'sotuv', 'dokonlar', 'ombor',
                        'mahsulotlar', 'xodimlar', 'savdolar',
                        'xarajatlar', 'mijozlar', 'sozlamalar']),
        'manager': set(['boshqaruv', 'sotuv', 'dokonlar', 'ombor',
                        'mahsulotlar', 'xodimlar', 'savdolar',
                        'xarajatlar', 'mijozlar']),
        'seller':  set(['sotuv', 'savdolar', 'mijozlar', 'ombor', 'mahsulotlar']),
    }

    for worker in Worker.objects.all():
        current  = set(worker.permissions or [])
        base     = ROLE_DEFAULTS.get(worker.role, set())
        added    = sorted(current - base)
        removed  = sorted(base - current)
        worker.extra_permissions = {'added': added, 'removed': removed}
        worker.save(update_fields=['extra_permissions'])


# ============================================================
# MIGRATION
# ============================================================

class Migration(migrations.Migration):

    dependencies = [
        ('accaunt', '0004_alter_worker_role_alter_worker_status'),
    ]

    operations = [
        # 1. Yangi permissions maydoni qo'shiladi (bo'sh ro'yxat bilan boshlanadi)
        migrations.AddField(
            model_name='worker',
            name='permissions',
            field=models.JSONField(
                blank=True,
                default=list,
                verbose_name='Ruxsatlar',
                help_text="Hodim kira oladigan bo'lim kodlari ro'yxati",
            ),
        ),

        # 2. Mavjud extra_permissions dan haqiqiy ruxsatlar hisoblab to'ldiriladi
        migrations.RunPython(
            migrate_to_permissions,
            reverse_code=reverse_to_extra_permissions,
        ),

        # 3. Eski extra_permissions maydoni o'chiriladi
        migrations.RemoveField(
            model_name='worker',
            name='extra_permissions',
        ),
    ]
