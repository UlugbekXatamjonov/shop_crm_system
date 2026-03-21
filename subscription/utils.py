"""
============================================================
SUBSCRIPTION — Yordamchi funksiyalar
============================================================
apply_lifo_deactivation(subscription)  — Downgrade/expiry: LIFO inactive
reactivate_downgraded_objects(sub)     — Upgrade: LIFO log orqali qaytarish
close_open_smenas(store)               — Ochiq smenalarni tizim yopadi
_blacklist_worker_tokens(worker)       — JWT tokenlarni bekor qilish
"""

import logging

from django.db import transaction
from django.utils import timezone

from .models import SubscriptionDowngradeLog

logger = logging.getLogger(__name__)


# ============================================================
# LIFO DEACTIVATION
# ============================================================

def apply_lifo_deactivation(subscription) -> dict:
    """
    Subscription tugaganda yoki downgrade bo'lganda
    limitdan ortiqcha ob'ektlarni LIFO tartibida inactive qiladi.

    Tartib (eng yangi → eng eski):
      Branch    — limit: plan.max_branches
      Warehouse — limit: plan.max_warehouses
      Worker    — limit: plan.max_workers (owner hech qachon inactive bo'lmaydi)
      Product   — HECH QACHON inactive qilinmaydi (tovar ma'lumoti)

    Qaytaradi: {'branches': N, 'warehouses': N, 'workers': N}
    """
    from store.models import Branch
    from warehouse.models import Warehouse
    from accaunt.models import Worker, WorkerRole

    plan  = subscription.plan
    store = subscription.store
    result = {'branches': 0, 'warehouses': 0, 'workers': 0}

    with transaction.atomic():
        # 1. Filiallar
        result['branches'] = _lifo_deactivate(
            subscription=subscription,
            model_class=Branch,
            queryset=Branch.objects.filter(
                store=store, status='active'
            ).order_by('-created_on'),
            max_count=plan.max_branches,
            object_type='Branch',
        )

        # 2. Omborlar
        result['warehouses'] = _lifo_deactivate(
            subscription=subscription,
            model_class=Warehouse,
            queryset=Warehouse.objects.filter(
                store=store, status='active'
            ).order_by('-created_on'),
            max_count=plan.max_warehouses,
            object_type='Warehouse',
        )

        # 3. Xodimlar (owner hech qachon deaktiv bo'lmaydi)
        result['workers'] = _lifo_deactivate(
            subscription=subscription,
            model_class=Worker,
            queryset=Worker.objects.filter(
                store=store,
                status='active',
            ).exclude(role=WorkerRole.OWNER).order_by('-created_on'),
            max_count=plan.max_workers,
            object_type='Worker',
        )

    logger.info(
        "LIFO deactivation: store=%s, plan=%s, result=%s",
        store.id, plan.plan_type, result
    )
    return result


def _lifo_deactivate(subscription, model_class, queryset, max_count, object_type) -> int:
    """
    Bir model uchun LIFO inactive qilish.

    max_count=0 → cheksiz, hech narsa qilinmaydi.
    Qaytaradi: inactive qilingan ob'ektlar soni.
    """
    if max_count == 0:
        return 0

    current = queryset.count()
    excess  = current - max_count
    if excess <= 0:
        return 0

    to_deactivate = list(queryset[:excess])

    for obj in to_deactivate:
        # Log yozish
        SubscriptionDowngradeLog.objects.create(
            subscription    = subscription,
            object_type     = object_type,
            object_id       = obj.pk,
            previous_status = obj.status,
        )
        # Inactive qilish
        model_class.objects.filter(pk=obj.pk).update(status='inactive')

        # Xodim bo'lsa — JWT tokenlarni bekor qilish
        if object_type == 'Worker':
            _blacklist_worker_tokens(obj)

        # Filial bo'lsa — ochiq smenalarni yopish
        if object_type == 'Branch':
            _close_branch_smenas(obj)

    return len(to_deactivate)


# ============================================================
# REACTIVATION (Upgrade bo'lganda)
# ============================================================

def reactivate_downgraded_objects(subscription) -> dict:
    """
    Upgrade bo'lganda DowngradeLog orqali ob'ektlarni qaytarish.

    Faqat previous_status='active' bo'lganlar qaytariladi.
    Tartib: eng avval inactive qilinganlar birinchi qaytariladi (FIFO order).
    Limit tekshiriladi: yangi plan limiti to'lsa qolganlar qaytarilmaydi.
    Ob'ekt bazada topilmasa → log yopiladi, jarayon to'xtamaydi.
    """
    from store.models import Branch
    from warehouse.models import Warehouse
    from accaunt.models import Worker

    model_map = {
        'Branch':    Branch,
        'Warehouse': Warehouse,
        'Worker':    Worker,
    }
    limit_attr_map = {
        'Branch':    'max_branches',
        'Warehouse': 'max_warehouses',
        'Worker':    'max_workers',
    }

    plan   = subscription.plan
    store  = subscription.store
    result = {'branches': 0, 'warehouses': 0, 'workers': 0, 'skipped': 0, 'not_found': 0}

    # Hozirgi active soni (har model uchun alohida kuzatiladi)
    current_counts = {}

    logs = SubscriptionDowngradeLog.objects.filter(
        subscription    = subscription,
        reactivated_at__isnull = True,
        previous_status = 'active',
    ).order_by('deactivated_at')   # eng eski birinchi

    for entry in logs:
        model_class = model_map.get(entry.object_type)
        if not model_class:
            _mark_log_done(entry, "Noma'lum ob'ekt turi")
            result['skipped'] += 1
            continue

        # Limit tekshirish
        limit_attr = limit_attr_map.get(entry.object_type, '')
        max_count  = getattr(plan, limit_attr, 0) if limit_attr else 0

        if max_count != 0:   # cheksiz emas
            if entry.object_type not in current_counts:
                current_counts[entry.object_type] = model_class.objects.filter(
                    store=store, status='active'
                ).count()
            if current_counts[entry.object_type] >= max_count:
                result['skipped'] += 1
                continue

        # Ob'ektni qaytarish
        try:
            model_class.objects.filter(pk=entry.object_id).update(status='active')
            _mark_log_done(entry)

            current_counts[entry.object_type] = (
                current_counts.get(entry.object_type, 0) + 1
            )
            plural_map = {
                'branch': 'branches',
                'warehouse': 'warehouses',
                'worker': 'workers',
            }
            key = plural_map.get(entry.object_type.lower(), entry.object_type.lower() + 's')
            result[key] = result.get(key, 0) + 1

        except Exception as exc:
            _mark_log_done(
                entry,
                note=f"{entry.object_type} #{entry.object_id} topilmadi yoki xato: {exc}"
            )
            result['not_found'] += 1

    logger.info(
        "Reactivation: store=%s, result=%s",
        store.id, result
    )
    return result


def _mark_log_done(entry, note: str = '') -> None:
    entry.reactivated_at = timezone.now()
    if note:
        entry.description = note
    entry.save(update_fields=['reactivated_at', 'description'])


# ============================================================
# SMENA YOPISH (tizim tomonidan)
# ============================================================

def close_open_smenas(store) -> int:
    """
    Do'kondagi barcha ochiq smenalarni tizim tomonidan yopadi.

    Qachon chaqiriladi:
      - Subscription expired bo'lganda
      - Branch inactive qilinganda (_lifo_deactivate orqali)

    worker_close = None → tizim yopdi.
    Qaytaradi: yopilgan smenalar soni.
    """
    from store.models import Smena, SmenaStatus

    open_smenas = Smena.objects.filter(store=store, status=SmenaStatus.OPEN)
    count = 0
    for smena in open_smenas:
        smena.worker_close = None
        smena.end_time     = timezone.now()
        smena.status       = SmenaStatus.CLOSED
        smena.description  = (
            smena.description + "\n" if smena.description else ""
        ) + "Tizim tomonidan yopildi: obuna cheklovi"
        smena.save()
        count += 1

    if count:
        logger.info("close_open_smenas: store=%s, yopildi=%d", store.id, count)
    return count


def _close_branch_smenas(branch) -> None:
    """Bitta filialning ochiq smenasini yopish."""
    from store.models import Smena, SmenaStatus

    Smena.objects.filter(
        branch=branch,
        status=SmenaStatus.OPEN,
    ).update(
        worker_close = None,
        end_time     = timezone.now(),
        status       = SmenaStatus.CLOSED,
        description  = "Tizim tomonidan yopildi: filial deaktiv (obuna cheklovi)",
    )


# ============================================================
# JWT TOKEN BEKOR QILISH
# ============================================================

def _blacklist_worker_tokens(worker) -> None:
    """
    Deaktiv qilingan xodimning barcha JWT tokenlarini bekor qiladi.
    django-simplejwt OutstandingToken / BlacklistedToken orqali.
    """
    try:
        from rest_framework_simplejwt.token_blacklist.models import (
            OutstandingToken, BlacklistedToken,
        )
        tokens = OutstandingToken.objects.filter(user=worker.user)
        for token in tokens:
            BlacklistedToken.objects.get_or_create(token=token)
        logger.info(
            "Worker %s tokenlari bekor qilindi (%d ta)",
            worker.id, tokens.count()
        )
    except Exception as exc:
        # Token blacklist o'rnatilmagan bo'lsa — jarayon to'xtamasin
        logger.warning("Token blacklist xatosi (worker=%s): %s", worker.id, exc)
