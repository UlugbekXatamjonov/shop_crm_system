"""
============================================================
WAREHOUSE APP — Celery Tasklar
============================================================
Tasklar:
  update_exchange_rates  — CBU API dan valyuta kurslarini olish (kunlik)
  check_low_stock        — Kam qoldiq mahsulotlarni tekshirish (har 6 soatda)

Celery Beat jadval (config/settings/base.py da belgilangan):
  update_exchange_rates → har kuni 09:00 da
  check_low_stock       → har 6 soatda (00:00, 06:00, 12:00, 18:00)
"""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


# ============================================================
# VALYUTA KURSI YANGILASH (BOSQICH 1.4)
# ============================================================

@shared_task(
    name='warehouse.tasks.update_exchange_rates',
    bind=True,
    max_retries=3,
    default_retry_delay=300,  # 5 daqiqadan keyin qayta urinish
)
def update_exchange_rates(self):
    """
    O'zbekiston Markaziy Banki (CBU) API dan valyuta kurslarini olish.

    API: https://cbu.uz/uz/arkhiv-kursov-valyut/json/
    Javob: [{"Ccy": "USD", "Rate": "12650.36", "Date": "03.03.2026", ...}, ...]

    Jarayon:
      1. CBU API ga so'rov yuborish
      2. Har bir valyuta uchun Currency modeli borligini tekshirish
      3. ExchangeRate.update_or_create — bugungi kurs yangilanadi
      4. Yangilangan va yangi kurslar soni log'ga yoziladi

    Retry: muvaffaqiyatsiz bo'lsa 5 daqiqadan keyin 3 martagacha qayta urinadi.
    """
    import requests
    from django.utils import timezone

    from .models import Currency, ExchangeRate

    CBU_API_URL = 'https://cbu.uz/uz/arkhiv-kursov-valyut/json/'
    today       = timezone.now().date()

    try:
        response = requests.get(CBU_API_URL, timeout=15)
        response.raise_for_status()
        data = response.json()

    except requests.exceptions.RequestException as exc:
        logger.error(f"CBU API xatosi: {exc}")
        raise self.retry(exc=exc)

    except Exception as exc:
        logger.error(f"CBU API javobini o'qishda xato: {exc}")
        raise self.retry(exc=exc)

    updated_count = 0
    created_count = 0
    skipped_count = 0

    for item in data:
        code = item.get('Ccy', '').upper().strip()
        rate_str = item.get('Rate', '').strip()

        if not code or not rate_str:
            continue

        # Faqat bizning tizimda mavjud valyutalar uchun
        try:
            currency = Currency.objects.get(code=code)
        except Currency.DoesNotExist:
            skipped_count += 1
            continue

        try:
            rate_value = float(rate_str.replace(',', '.'))
        except (ValueError, AttributeError):
            logger.warning(f"Noto'g'ri kurs qiymati: {code} = {rate_str!r}")
            continue

        _, created = ExchangeRate.objects.update_or_create(
            currency=currency,
            date=today,
            defaults={
                'rate': rate_value,
            },
        )

        if created:
            created_count += 1
        else:
            updated_count += 1

    logger.info(
        f"Valyuta kurslari yangilandi ({today}): "
        f"yangi={created_count}, yangilangan={updated_count}, o'tkazib yuborildi={skipped_count}"
    )

    return {
        'date':    str(today),
        'created': created_count,
        'updated': updated_count,
        'skipped': skipped_count,
    }


# ============================================================
# KAM QOLDIQ TEKSHIRISH (BOSQICH 15)
# ============================================================

@shared_task(
    name='warehouse.tasks.check_low_stock',
    bind=True,
    max_retries=2,
    default_retry_delay=60,
)
def check_low_stock(self):
    """
    Har 6 soatda: barcha do'konlar bo'yicha kam qoldiq mahsulotlarni aniqlash.

    Mantiq:
      1. StoreSettings.low_stock_enabled=True bo'lgan do'konlarni olish
      2. Har do'kon uchun Stock.quantity <= low_stock_threshold bo'lganlarni topish
         (quantity > 0: tugab ketganlar emas, yaqinlashganlar)
      3. Natija log ga yoziladi
      4. Kelajakda: Telegram/SMS xabar yuborish (v2) — bu yerda placeholder

    Qaytaradi:
      {
        'checked_stores': int,
        'low_stock_items': int,
        'details': [{'store': str, 'product': str, 'quantity': float, 'threshold': int}, ...]
      }
    """
    from django.db.models import F

    from store.models import StoreSettings
    from .models import Stock

    try:
        # Low stock yoqilgan do'konlar uchun StoreSettings ni olish
        settings_qs = (
            StoreSettings.objects
            .filter(low_stock_enabled=True)
            .select_related('store')
        )

        checked_stores = 0
        low_stock_items = 0
        details = []

        for store_settings in settings_qs:
            store     = store_settings.store
            threshold = store_settings.low_stock_threshold

            # Threshold dan kam (lekin 0 dan ko'p) stoklar
            low_stocks = (
                Stock.objects
                .filter(
                    product__store=store,
                    quantity__gt=0,
                    quantity__lte=threshold,
                )
                .select_related('product', 'branch', 'warehouse')
            )

            checked_stores += 1

            for stock in low_stocks:
                low_stock_items += 1
                location = (
                    stock.branch.name if stock.branch_id
                    else (stock.warehouse.name if stock.warehouse_id else '—')
                )
                details.append({
                    'store'    : store.name,
                    'product'  : stock.product.name,
                    'location' : location,
                    'quantity' : float(stock.quantity),
                    'threshold': threshold,
                })
                logger.warning(
                    f"[KAM QOLDIQ] Do'kon: '{store.name}' | "
                    f"Mahsulot: '{stock.product.name}' ({location}) | "
                    f"Qoldiq: {stock.quantity} <= {threshold}"
                )

        logger.info(
            f"Kam qoldiq tekshiruvi tugadi: "
            f"tekshirildi={checked_stores} do'kon, "
            f"muammo={low_stock_items} mahsulot"
        )

        # TODO (v2): Telegram/SMS orqali do'kon egasiga xabar yuborish
        # if low_stock_items > 0:
        #     send_telegram_notification.delay(store_id, low_stock_items)

        return {
            'checked_stores' : checked_stores,
            'low_stock_items': low_stock_items,
            'details'        : details,
        }

    except Exception as exc:
        logger.error(f"check_low_stock xatosi: {exc}")
        raise self.retry(exc=exc)
