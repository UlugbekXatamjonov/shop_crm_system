"""
============================================================
SUBSCRIPTION — Celery Tasklari
============================================================
check_subscription_expiry()  — Har kuni 00:01 da ishlaydi:
  1. 10/3/1 kun qolgan subscriptionlarga ogohlantirish yuboradi
  2. Muddati tugagan subscriptionlarni 'expired' ga o'tkazadi
  3. Expired subscriptionlarda LIFO inactive qiladi
  4. Ochiq smenalarni yopadi

Idempotentlik:
  notified_*d flaglari tufayli bir ogohlantirish bir marta yuboriladi.
  Expired tekshiruvi qayta ishlansa ham zarar yo'q (allaqachon expired).

settings.py:
  SUBSCRIPTION_TRIAL_DAYS    = 30
  SUBSCRIPTION_EXPIRY_NOTIFY = [10, 3, 1]
  SUBSCRIPTION_CACHE_TTL     = 3600
"""

import logging
from datetime import date, timedelta

from celery import shared_task
from django.conf import settings

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def check_subscription_expiry(self):
    """
    Kunlik obuna tekshiruvi — har kuni 00:01 da ishlaydi.

    Bajaradigan ishlari:
      1. 10/3/1 kun qolgan obunalarga ogohlantirish
      2. Muddati tugaganlarni expired ga o'tkazish
      3. Expired'larda LIFO deactivation
      4. Ochiq smenalarni yopish
      5. Redis keshni tozalash
    """
    try:
        _run_expiry_check()
    except Exception as exc:
        logger.exception("check_subscription_expiry xatosi: %s", exc)
        raise self.retry(exc=exc, countdown=300)  # 5 daqiqadan keyin qayta


def _run_expiry_check():
    from subscription.models import Subscription, SubscriptionStatus
    from subscription.utils import apply_lifo_deactivation, close_open_smenas
    from config.cache_utils import invalidate_subscription_cache

    today        = date.today()
    notify_days  = getattr(settings, 'SUBSCRIPTION_EXPIRY_NOTIFY', [10, 3, 1])

    # ---- 1. Ogohlantirish ----
    flag_map = {10: 'notified_10d', 3: 'notified_3d', 1: 'notified_1d'}

    for days in notify_days:
        flag = flag_map.get(days)
        if not flag:
            continue

        target_date = today + timedelta(days=days)
        subs = Subscription.objects.filter(
            status__in=[SubscriptionStatus.TRIAL, SubscriptionStatus.ACTIVE],
            end_date=target_date,
        ).filter(**{flag: False}).select_related('store', 'plan')

        for sub in subs:
            _send_expiry_notification(sub, days_left=days)
            setattr(sub, flag, True)
            sub.save(update_fields=[flag])
            logger.info(
                "Ogohlantirish yuborildi: store='%s' (%d kun qoldi)",
                sub.store.name, days
            )

    # ---- 2. Expired bo'lganlar ----
    expired_subs = Subscription.objects.filter(
        status__in=[SubscriptionStatus.TRIAL, SubscriptionStatus.ACTIVE],
        end_date__lt=today,
    ).select_related('store', 'plan')

    for sub in expired_subs:
        # Status o'zgartirish
        sub.status = SubscriptionStatus.EXPIRED
        sub.save(update_fields=['status', 'updated_on'])

        # LIFO deactivation
        result = apply_lifo_deactivation(sub)

        # Ochiq smenalarni yopish
        closed = close_open_smenas(sub.store)

        # Redis keshni tozalash
        invalidate_subscription_cache(sub.store_id)

        logger.info(
            "Subscription expired: store='%s', LIFO=%s, smena yopildi=%d",
            sub.store.name, result, closed
        )


def _send_expiry_notification(subscription, days_left: int) -> None:
    """
    Obuna tugash ogohlantirishini yuborish.

    Hozircha: faqat log (Telegram/SMS B11/B11.5 da qo'shiladi).
    """
    store    = subscription.store
    plan     = subscription.plan
    end_date = subscription.end_date

    message = (
        f"⚠️ Obuna ogohlantirishi\n"
        f"Do'kon: {store.name}\n"
        f"Tarif: {plan.name}\n"
        f"Tugash sanasi: {end_date}\n"
        f"Qolgan kunlar: {days_left}\n"
        f"To'lov qilish: /api/v1/subscription/pay/"
    )

    logger.info("NOTIFICATION: %s", message)

    # TODO: B11 Telegram bot tayyor bo'lganda shu yerda yuboriladi:
    # if store.settings.telegram_enabled and store.settings.telegram_chat_id:
    #     send_telegram_message(store.settings.telegram_chat_id, message)
