"""
============================================================
CELERY KONFIGURATSIYA
============================================================
Celery — asinxron vazifalarni bajarish uchun kutubxona.

Bu fayl Celery ni Django bilan bog'laydi va barcha
vazifalar (tasks) avtomatik topilishini ta'minlaydi.

Ishlatilish joylari:
  - Excel/PDF eksport (background da)
  - Email yuborish
  - Subscription tugashini tekshirish
  - Kam mahsulot ogohlantirishlari
  - Kechasi zaxira nusxa (backup)
"""

import os
from celery import Celery

# Celery uchun Django settings modulini belgilash
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')

# Celery ilovasini yaratish
app = Celery('config')

# Django settings dan CELERY_ prefiksli barcha sozlamalarni olish
app.config_from_object('django.conf:settings', namespace='CELERY')

# Barcha o'rnatilgan ilovalardagi tasks.py fayllarini avtomatik topish
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """
    Test vazifasi — Celery ishlayotganini tekshirish uchun.
    Ishlatish: from config.celery import debug_task; debug_task.delay()
    """
    print(f'Celery ishlayapti! Task ID: {self.request.id}')
