"""
============================================================
STORE APP — Signallar
============================================================
Signallar:
  create_store_settings — Store yaratilganda StoreSettings AVTOMATIK yaratadi

⚠️ QOIDA 1 (HECH QACHON UNUTMA):
  Store yaratilganda AVTOMATIK default StoreSettings yaratilishi SHART.
  Sabab: Hech qachon "sozlamalar topilmadi" xatosi bo'lmasligi kerak.

Bu signal store/apps.py da StoreConfig.ready() orqali ulanadi.
"""

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Store, StoreSettings

logger = logging.getLogger(__name__)


# ============================================================
# QOIDA 1 — STORE YARATILGANDA STORESETTINGS AUTO-YARATISH
# ============================================================

@receiver(post_save, sender=Store)
def create_store_settings(sender, instance: Store, created: bool, **kwargs) -> None:
    """
    Store yaratilganda avtomatik StoreSettings yaratadi.

    get_or_create ishlatiladi — ikkilanib chaqirilsa ham xato bo'lmaydi.
    created=False bo'lsa (update) — hech narsa qilinmaydi.
    """
    if created:
        settings_obj, was_created = StoreSettings.objects.get_or_create(
            store=instance
        )
        if was_created:
            logger.info(
                f"StoreSettings avtomatik yaratildi: do'kon='{instance.name}' (id={instance.id})"
            )
        else:
            logger.warning(
                f"StoreSettings allaqachon mavjud edi: do'kon='{instance.name}' (id={instance.id})"
            )
