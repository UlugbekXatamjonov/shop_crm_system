#!/bin/sh
# ============================================================
# RAILWAY DEPLOY ENTRYPOINT
# ============================================================
# Barcha stdout va stderr ni birlashtiradi — Railway Deploy Logs
# da hammasi ko'rinadi.
# ============================================================

# Barcha stderr ni stdout ga yo'naltirish (Railway Deploy Logs uchun)
exec 2>&1

# Xato yuz bersa darhol to'xtash
set -e

echo "============================================"
echo "[STARTUP] PORT = ${PORT:-8000}"
echo "[STARTUP] DJANGO_SETTINGS_MODULE = ${DJANGO_SETTINGS_MODULE}"
echo "============================================"

# 1. Ma'lumotlar bazasini migrate qilish
echo "[STARTUP] Running database migrations..."
python manage.py migrate --settings=config.settings.production
echo "[STARTUP] Migrations complete."

# 2. Gunicorn ishga tushirish
echo "[STARTUP] Starting Gunicorn on 0.0.0.0:${PORT:-8000} ..."
exec gunicorn config.wsgi:application \
    --bind "0.0.0.0:${PORT:-8000}" \
    --workers 2 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
