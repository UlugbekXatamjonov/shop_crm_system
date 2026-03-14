"""
============================================================
ACCAUNT APP — Celery Tasklar
============================================================
Tasklar:
  generate_monthly_worker_kpi — Oylik WorkerKPI yozuvlarini yaratish

Celery Beat jadval (config/settings/base.py da belgilangan):
  generate_monthly_worker_kpi → har oy 1-kuni soat 00:01 da
"""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


# ============================================================
# OYLIK WORKERKPI GENERATSIYA (BOSQICH 15)
# ============================================================

@shared_task(
    name='accaunt.tasks.generate_monthly_worker_kpi',
    bind=True,
    max_retries=3,
    default_retry_delay=300,
)
def generate_monthly_worker_kpi(self):
    """
    Har oy 1-kuni 00:01 da: joriy oy+yil uchun barcha aktiv xodimlar
    bo'yicha WorkerKPI yozuvini get_or_create qilish.

    Mantiq:
      1. StoreSettings.kpi_enabled=True bo'lgan do'konlarni olish
      2. Shu do'konlardagi ACTIVE xodimlarni olish (owner dan tashqari)
      3. Joriy oy+yil uchun WorkerKPI get_or_create
      4. Yaratilganlar soni log ga yoziladi

    Natija:
      {'month': int, 'year': int, 'created': int, 'existed': int}
    """
    try:
        from django.utils import timezone

        from store.models import StoreSettings
        from .models import Worker, WorkerKPI, WorkerStatus

        now   = timezone.now()
        month = now.month
        year  = now.year

        # kpi_enabled=True bo'lgan do'konlar
        enabled_store_ids = (
            StoreSettings.objects
            .filter(kpi_enabled=True)
            .values_list('store_id', flat=True)
        )

        # Shu do'konlardagi aktiv xodimlar (owner dan tashqari — owner KPI tutmaydi)
        workers = (
            Worker.objects
            .filter(
                store_id__in=enabled_store_ids,
                status=WorkerStatus.ACTIVE,
            )
            .exclude(role='owner')
            .select_related('store')
        )

        created_count = 0
        existed_count = 0

        for worker in workers:
            _, created = WorkerKPI.objects.get_or_create(
                worker=worker,
                store=worker.store,
                month=month,
                year=year,
            )
            if created:
                created_count += 1
            else:
                existed_count += 1

        logger.info(
            f"Oylik WorkerKPI generatsiya ({month}/{year}): "
            f"yaratildi={created_count}, mavjud={existed_count}"
        )

        return {
            'month'  : month,
            'year'   : year,
            'created': created_count,
            'existed': existed_count,
        }

    except Exception as exc:
        logger.error(f"generate_monthly_worker_kpi xatosi: {exc}")
        raise self.retry(exc=exc)
