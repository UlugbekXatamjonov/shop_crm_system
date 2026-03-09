"""
============================================================
WAREHOUSE APP — Yordamchi funksiyalar
============================================================
Funksiyalar:
  generate_unique_barcode(store_id)  — EAN-13 barcode generatsiya
  get_barcode_image(barcode_value)   — PNG rasm qaytaradi
  get_barcode_svg(barcode_value)     — SVG qaytaradi
  get_today_rate(currency_code)      — Bugungi valyuta kursini olish
  generate_batch_code(store)         — FIFO partiya kodi generatsiya
  fifo_deduct(product, loc_kwargs, qty_needed) — FIFO bo'yicha partiyadan yechib olish
"""

from decimal import Decimal
from io import BytesIO


# ============================================================
# BARCODE GENERATSIYA (EAN-13)
# ============================================================

def _ean13_check_digit(code_12: str) -> str:
    """
    EAN-13 tekshirish raqamini hisoblash.
    Standart EAN-13 algoritmi:
      - Toq pozitsiyalar (0,2,4,...) × 1
      - Juft pozitsiyalar (1,3,5,...) × 3
      - Yig'indini 10 ga bo'lgandagi qoldiqni 10 dan ayirish
    """
    total = 0
    for i, digit in enumerate(code_12):
        weight = 1 if i % 2 == 0 else 3
        total += int(digit) * weight
    check = (10 - (total % 10)) % 10
    return str(check)


def generate_unique_barcode(store_id: int) -> str:
    """
    Do'kon uchun unikal EAN-13 barcode generatsiya qilish.

    Format (13 raqam):
      20XXXXXYYYYY C
      ──┬── ──┬── ┬ ┬
        │     │   │ └─ EAN-13 tekshirish raqami (auto)
        │     │   └─── 5 ta ketma-ketlik raqami (00001-99999)
        │     └─────── 5 ta do'kon ID (00001-99999)
        └───────────── GS1 in-store prefix "20"

    Natija: Hech qachon real GS1 mahsulot barcodeiga to'qnashmaydi.
    Maksimal: har bir do'kon uchun 99,999 ta barcode.
    """
    from .models import Product

    prefix = f"20{store_id:05d}"  # 7 ta raqam: "20" + 5 ta store_id

    # Mavjud barcodelardan maksimal ketma-ketlik raqamini topish
    existing_barcodes = (
        Product.objects
        .filter(store_id=store_id, barcode__startswith=prefix)
        .exclude(barcode__isnull=True)
        .values_list('barcode', flat=True)
    )

    max_seq = 0
    for bc in existing_barcodes:
        try:
            # 7-12 pozitsiyalar — 5 ta ketma-ketlik raqami
            seq = int(str(bc)[7:12])
            if seq > max_seq:
                max_seq = seq
        except (ValueError, IndexError):
            pass

    next_seq = max_seq + 1
    if next_seq > 99999:
        raise ValueError(
            f"Do'kon {store_id} uchun barcode limiti to'ldi (maksimal: 99,999)."
        )

    # 12 ta raqam (check digit qo'shilmagan)
    code_12 = f"{prefix}{next_seq:05d}"
    check   = _ean13_check_digit(code_12)

    return f"{code_12}{check}"  # 13 ta raqam


def get_barcode_image(barcode_value: str) -> bytes:
    """
    Barcode PNG rasmi generatsiya qilish.
    python-barcode + Pillow ishlatiladi.

    Qaytaradi: PNG format bytes
    """
    try:
        import barcode as barcode_lib
        from barcode.writer import ImageWriter

        # EAN-13: 12 ta raqam berish kerak (check digit auto qo'shiladi)
        code_12 = barcode_value[:12] if len(barcode_value) == 13 else barcode_value

        writer = ImageWriter()
        ean = barcode_lib.get('ean13', code_12, writer=writer)

        output = BytesIO()
        ean.write(output, options={
            'write_text': True,
            'font_size':  10,
            'text_distance': 5,
            'quiet_zone': 6,
            'dpi': 300,
        })
        output.seek(0)
        return output.read()

    except Exception as e:
        raise ValueError(f"Barcode PNG generatsiya xatosi: {e}")


def get_barcode_svg(barcode_value: str) -> bytes:
    """
    Barcode SVG generatsiya qilish.
    python-barcode ishlatiladi (Pillow shart emas).

    Qaytaradi: SVG format bytes
    """
    try:
        import barcode as barcode_lib
        from barcode.writer import SVGWriter

        code_12 = barcode_value[:12] if len(barcode_value) == 13 else barcode_value

        writer = SVGWriter()
        ean    = barcode_lib.get('ean13', code_12, writer=writer)

        output = BytesIO()
        ean.write(output)
        output.seek(0)
        return output.read()

    except Exception as e:
        raise ValueError(f"Barcode SVG generatsiya xatosi: {e}")


# ============================================================
# VALYUTA KURSI YORDAMCHISI
# ============================================================

def get_today_rate(currency_code: str) -> float | None:
    """
    Berilgan valyutaning bugungi kursini UZS da qaytaradi.
    Agar bugungi kurs yo'q bo'lsa — eng oxirgi mavjud kursni qaytaradi.
    UZS uchun → 1.0 qaytaradi.
    Topilmasa → None qaytaradi.

    Ishlatish:
      rate = get_today_rate('USD')
      if rate:
          uzs_price = usd_price * rate
    """
    if currency_code.upper() == 'UZS':
        return 1.0

    from .models import ExchangeRate
    from django.utils import timezone

    today = timezone.now().date()

    # Bugungi kurs
    rate_obj = (
        ExchangeRate.objects
        .filter(currency__code=currency_code.upper(), date=today)
        .select_related('currency')
        .first()
    )

    if rate_obj:
        return float(rate_obj.rate)

    # Oxirgi mavjud kurs
    last_rate = (
        ExchangeRate.objects
        .filter(currency__code=currency_code.upper())
        .select_related('currency')
        .order_by('-date')
        .first()
    )

    if last_rate:
        return float(last_rate.rate)

    return None


# ============================================================
# FIFO PARTIYA KODI GENERATSIYA
# ============================================================

def generate_batch_code(store) -> str:
    """
    Do'kon uchun FIFO partiya kodi generatsiya qilish.

    Format: S{store_id}-{YY}-{MM}-{DD}-{seq:04d}
    Misol:  S1-26-03-10-0001
      S1     — do'kon ID si (unikal, to'qnashish bo'lmaydi)
      26-03-10 — 2026-yil 10-mart (qisqa sana formati)
      0001   — shu kun uchun birinchi partiya

    Eski format: {DO'KON[:5].upper()}-YY-MM-DD-seq — bir xil nomdagi
    do'konlar to'qnashishi mumkin edi. Yangi format store.id orqali
    har doim unikal.

    Thread-safe: select_for_update() + transaction.atomic() ichida ishlaydi.
    Kod benzersizligi: unique=True bilan DB darajasida kafolatlanadi.

    Maksimal kuniga: 9999 ta partiya (bir do'kon uchun).
    """
    from django.db import transaction
    from django.db.models import Q
    from django.utils import timezone
    from .models import StockBatch

    today  = timezone.localdate()
    prefix = f"S{store.id}-{today.strftime('%y-%m-%d')}-"

    with transaction.atomic():
        # Bugungi kundagi so'nggi partiyani toping (select_for_update — thread-safe)
        last = (
            StockBatch.objects
            .filter(batch_code__startswith=prefix)
            .select_for_update()
            .order_by('-batch_code')
            .first()
        )
        if last:
            # Oxirgi ketma-ketlik raqamini ajratib oling va 1 ga oshiring
            try:
                seq = int(last.batch_code.rsplit('-', 1)[1]) + 1
            except (ValueError, IndexError):
                seq = 1
        else:
            seq = 1

        return f"{prefix}{seq:04d}"


# ============================================================
# FIFO YECHIB OLISH (chiqim/sotuv/transfer uchun)
# ============================================================

def fifo_deduct(product, location_kwargs: dict, qty_needed: Decimal):
    """
    FIFO bo'yicha partiyalardan yechib olish.

    Argumentlar:
      product        — warehouse.Product obyekti
      location_kwargs — {'branch': branch, 'warehouse': None} yoki
                        {'branch': None,   'warehouse': warehouse}
      qty_needed     — yechib olinishi kerak bo'lgan umumiy miqdor (Decimal)

    Qaytaradi: (deductions, total_cost)
      deductions  — [(StockBatch, qty_used), ...] ro'yxati (FIFO tartibi)
      total_cost  — Decimal, jami tannarx = sum(qty_used * unit_cost)

    MUHIM:
      - Bu funksiya select_for_update() ishlatadi.
      - transaction.atomic() ichida chaqirilishi shart!
      - Agar qoldiq yetishmasa, qolgan miqdor o'chirilmaydi.
        (Chaqiruvchi kod oldin Stock.quantity tekshirishi kerak.)

    Misol:
      >>> deductions, total_cost = fifo_deduct(
      ...     product, {'branch': branch, 'warehouse': None}, Decimal('8')
      ... )
      >>> avg_cost = total_cost / Decimal('8')
    """
    from django.db.models import F
    from .models import StockBatch

    batches = (
        StockBatch.objects
        .select_for_update()
        .filter(product=product, qty_left__gt=0, **location_kwargs)
        .order_by('received_at', 'id')  # FIFO: eng eski birinchi
    )

    remaining  = qty_needed
    deductions = []           # [(batch, qty_used), ...]
    total_cost = Decimal('0')

    for batch in batches:
        if remaining <= 0:
            break
        use = min(batch.qty_left, remaining)
        deductions.append((batch, use))
        total_cost += use * batch.unit_cost
        # F() expression bilan atomik yangilash (race condition yo'q)
        StockBatch.objects.filter(pk=batch.pk).update(
            qty_left=F('qty_left') - use
        )
        remaining -= use

    return deductions, total_cost
