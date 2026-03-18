"""
============================================================
CONFIG — Redis Kesh Yordamchi Funksiyalari
============================================================
Funksiyalar:
  get_store_settings(store_id)    — StoreSettings ni Redis keshdan olish
  invalidate_store_settings(...)  — Keshni tozalash (settings o'zgarganda)

⚠️ QOIDA 3 (HECH QACHON UNUTMA):
  StoreSettings ga har safar DB ga borish — 200 do'kon × ko'p so'rov = sekin.
  Yechim: Redis kesh, 5 daqiqa TTL.

Ishlatish (istalgan ViewSet da):
  from config.cache_utils import get_store_settings, invalidate_store_settings

  # Tekshirish:
  settings = get_store_settings(request.user.worker.store_id)
  if not settings.allow_debt:
      raise ValidationError("Nasiya bu do'konda o'chirilgan.")

  # Sozlamalar o'zgarganda — keshni tozalash:
  invalidate_store_settings(store_id)
"""

import logging

from django.core.cache import cache

logger = logging.getLogger(__name__)

# Kesh kaliti formati
_SETTINGS_KEY = 'store_settings_{store_id}'

# TTL: 5 daqiqa (300 soniya)
_SETTINGS_TTL = 300


def get_store_settings(store_id: int):
    """
    StoreSettings obyektini Redis keshdan olish.

    Keshda bo'lmasa → DB dan oladi va keshga yozadi.
    DB da ham bo'lmasa (signal ishlamamagan bo'lsa) → yaratadi.

    Qaytaradi: StoreSettings obyekt
    Raises: StoreSettings.DoesNotExist (agar store topilmasa)
    """
    from store.models import StoreSettings

    cache_key = _SETTINGS_KEY.format(store_id=store_id)

    # 1. Keshdan olishga urinish
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    # 2. DB dan olish
    try:
        settings_obj = (
            StoreSettings.objects
            .select_related('store')
            .get(store_id=store_id)
        )
    except StoreSettings.DoesNotExist:
        # Signal ishlamagan yoki eski do'kon — avtomatik yaratamiz
        from store.models import Store
        store = Store.objects.get(id=store_id)
        settings_obj, created = StoreSettings.objects.get_or_create(store=store)
        if created:
            logger.warning(
                f"get_store_settings: StoreSettings topilmadi, yaratildi "
                f"(store_id={store_id}). Signal to'g'ri ulanganmi?"
            )

    # 3. Keshga yozish
    cache.set(cache_key, settings_obj, timeout=_SETTINGS_TTL)
    return settings_obj


def invalidate_subscription_cache(store_id: int) -> None:
    """
    Do'kon obuna keshini tozalash.

    Qachon chaqirish kerak:
      - AdminSubscriptionViewSet da plan/status o'zgarganda
      - To'lov qo'shilganda
      - Celery task da subscription expired bo'lganda

    Keyingi get_subscription() chaqiruvida DB dan yangi ma'lumot olinadi.
    """
    from django.conf import settings as django_settings
    cache_key = f'subscription_{store_id}'
    cache.delete(cache_key)
    logger.debug(f"Subscription keshi tozalandi: store_id={store_id}")


def get_subscription(store_id: int):
    """
    Subscription obyektini Redis keshdan olish.

    TTL: settings.SUBSCRIPTION_CACHE_TTL (default: 3600 — 1 soat)
    Keshda yo'q bo'lsa → DB dan oladi va keshga yozadi.
    Subscription yo'q bo'lsa → None qaytaradi.
    """
    from django.conf import settings as django_settings
    from subscription.models import Subscription

    cache_key = f'subscription_{store_id}'
    ttl       = getattr(django_settings, 'SUBSCRIPTION_CACHE_TTL', 3600)

    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        sub = (
            Subscription.objects
            .select_related('plan', 'store')
            .get(store_id=store_id)
        )
    except Subscription.DoesNotExist:
        logger.warning(f"get_subscription: store_id={store_id} uchun obuna topilmadi.")
        return None

    cache.set(cache_key, sub, timeout=ttl)
    return sub


def invalidate_store_settings(store_id: int) -> None:
    """
    Do'kon sozlamalari keshini tozalash.

    Qachon chaqirish kerak:
      - StoreSettingsViewSet.perform_update() da
      - Boshqa joylarda StoreSettings o'zgartirilganda

    Keyingi get_store_settings() chaqiruvida DB dan yangi ma'lumot olinadi.
    """
    cache_key = _SETTINGS_KEY.format(store_id=store_id)
    cache.delete(cache_key)
    logger.debug(f"StoreSettings keshi tozalandi: store_id={store_id}")
