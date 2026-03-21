"""
============================================================
ACCAUNT APP — Custom Throttle Klasslari
============================================================
API so'rovlar chastotasini cheklash uchun throttle klasslari.

Throttle tiplari va qo'llanilish joylari:
  LoginThrottle       — POST /auth/login/             5/min
  RegisterThrottle    — POST /auth/register/           3/min
  PasswordResetThrottle — POST /auth/send-reset-email/ 3/hour
  ExportThrottle      — GET /export/*                  5/min
  BulkOperationThrottle — bulk/ endpointlar           10/min

Sozlamalar (settings.py da DEFAULT_THROTTLE_RATES):
  login      → 5/min
  register   → 3/min
  password_reset → 3/hour
  export     → 5/min
  bulk       → 10/min
"""

from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class LoginThrottle(AnonRateThrottle):
    """
    Login so'rovlari uchun throttle.
    Anonim IP asosida — brute-force himoya.
    """
    scope = 'login'


class RegisterThrottle(AnonRateThrottle):
    """
    Ro'yxatdan o'tish uchun throttle.
    Anonim IP asosida — spam/bot himoya.
    """
    scope = 'register'


class PasswordResetThrottle(AnonRateThrottle):
    """
    Parol tiklash email yuborish uchun throttle.
    Email tizimini zo'riqtirmaslik uchun soatiga 3 ta.
    """
    scope = 'password_reset'


class ExportThrottle(UserRateThrottle):
    """
    Export endpointlari uchun throttle.
    Foydalanuvchi asosida — katta Excel/PDF generatsiyani cheklash.
    """
    scope = 'export'


class BulkOperationThrottle(UserRateThrottle):
    """
    Bulk operatsiyalar uchun throttle.
    Foydalanuvchi asosida — bulk movements, bulk price update va h.k.
    """
    scope = 'bulk'
