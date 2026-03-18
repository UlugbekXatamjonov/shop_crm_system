"""
============================================================
SUBSCRIPTION — Signallar
============================================================
Store yaratilganda → Trial subscription avtomatik yaratiladi.

Trial rejasi SubscriptionPlan da mavjud bo'lishi shart.
Agar Trial rejasi topilmasa → ogohlantirish logg'ga yoziladi,
xatolik ko'tarilmaydi (Store yaratilishiga to'siq bo'lmasin).
"""

import logging
from datetime import date, timedelta

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(post_save, sender='store.Store')
def create_trial_subscription(sender, instance, created, **kwargs):
    """
    Yangi Store yaratilganda 30 kunlik Trial obuna avtomatik qo'shiladi.

    Trial davri: settings.SUBSCRIPTION_TRIAL_DAYS (default: 30)
    Trial rejasi: SubscriptionPlan(plan_type='trial')
    """
    if not created:
        return

    from subscription.models import Subscription, SubscriptionPlan, SubscriptionStatus

    try:
        trial_plan = SubscriptionPlan.objects.get(plan_type='trial')
    except SubscriptionPlan.DoesNotExist:
        logger.warning(
            "create_trial_subscription: 'trial' tarif rejasi topilmadi. "
            "Store #%s uchun obuna yaratilmadi. "
            "Django admin orqali 'trial' rejasini yarating.",
            instance.id,
        )
        return

    trial_days = getattr(settings, 'SUBSCRIPTION_TRIAL_DAYS', 30)
    today      = date.today()

    Subscription.objects.create(
        store      = instance,
        plan       = trial_plan,
        status     = SubscriptionStatus.TRIAL,
        start_date = today,
        end_date   = today + timedelta(days=trial_days),
    )
    logger.info(
        "Trial obuna yaratildi: store='%s' (#%s), %d kun",
        instance.name, instance.id, trial_days,
    )
