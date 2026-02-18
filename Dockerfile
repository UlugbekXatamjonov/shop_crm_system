# ============================================================
# DOCKERFILE — Django CRM tizimi uchun
# ============================================================
# Python 3.12 slim (yengil) rasmidan boshlaymiz
# ============================================================

FROM python:3.12-slim

# ============================================================
# TIZIM SOZLAMALARI
# ============================================================

# Python out: konsolga to'g'ridan-to'g'ri chiqaradi (buffer yo'q)
ENV PYTHONUNBUFFERED=1

# .pyc fayllar yaratilmaydi (konteynerda kerak emas)
ENV PYTHONDONTWRITEBYTECODE=1

# ============================================================
# TIZIM KUTUBXONALARI
# ============================================================

RUN apt-get update && apt-get install -y --no-install-recommends \
    # PostgreSQL bilan ishlash uchun
    libpq-dev \
    # gcc — C kutubxonalarini kompilyatsiya qilish uchun
    gcc \
    # Barcode va QR kod uchun
    libzbar0 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ============================================================
# ISHCHI FOYDALANUVCHI (Xavfsizlik uchun root bo'lmasin)
# ============================================================

# Non-root foydalanuvchi yaratish
RUN groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

# ============================================================
# ILOVA KOD
# ============================================================

# Ishchi papka
WORKDIR /app

# Avval requirements — Docker kesh qatlamlaridan foydalanish uchun
COPY requirements/ requirements/
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements/production.txt

# Keyin barcha kodlar
COPY . .

# Statik fayllar to'planadi (nginx uzatadi)
RUN python manage.py collectstatic --noinput --settings=config.settings.production || true

# Logs papkasini yaratish
RUN mkdir -p logs && chown -R appuser:appuser /app

# ============================================================
# FOYDALANUVCHINI O'ZGARTIRISH
# ============================================================

USER appuser

# ============================================================
# PORT VA ISHGA TUSHIRISH
# ============================================================

# Django porti
EXPOSE 8000

# Gunicorn bilan ishga tushirish
# --workers: CPU core soni × 2 + 1 (masalan, 2 core → 5 worker)
CMD ["gunicorn", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "3", \
     "--worker-class", "sync", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "config.wsgi:application"]
