"""
============================================================
Custom Exception Handler — O'zbek tilidagi xato xabarlari
============================================================
Barcha HTTP xato kodlari uchun o'zbek tilidagi
tushunarli xabarlar qaytaradi.

Qo'llash: REST_FRAMEWORK['EXCEPTION_HANDLER'] da ro'yxatdan o'tkaziladi.
"""

from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status as http_status


# HTTP status kodlari uchun o'zbek tilidagi xabarlar
UZBEK_ERROR_MESSAGES = {
    400: "So'rov ma'lumotlari noto'g'ri.",
    401: "Tizimga kirish talab etiladi. Iltimos, avval login qiling.",
    403: "Bu amalni bajarishga ruxsatingiz yo'q.",
    404: "So'ralgan ma'lumot topilmadi.",
    405: "Bu so'rov turi ({method}) qo'llab-quvvatlanmaydi.",
    406: "So'ralgan format qabul qilinmaydi.",
    415: "Yuborilgan fayl turi qo'llab-quvvatlanmaydi.",
    429: "So'rovlar soni limitdan oshdi. Keyinroq urinib ko'ring.",
    500: "Server xatosi yuz berdi. Iltimos, keyinroq urinib ko'ring.",
    503: "Xizmat vaqtincha mavjud emas. Keyinroq urinib ko'ring.",
}


def custom_exception_handler(exc, context):
    """
    DRF ning standart exception handler ustiga qurilgan.
    'detail' maydoni bo'lgan barcha xatolarda o'zbek tilidagi
    xabar qaytaradi.
    """
    # Avval DRF ning standart handleri ishga tushadi
    response = exception_handler(exc, context)

    if response is not None:
        status_code = response.status_code
        uzbek_msg   = UZBEK_ERROR_MESSAGES.get(status_code)

        if uzbek_msg:
            # Faqat 'detail' kalit so'zi bo'lgan oddiy xatolarda almashtirish
            # (validation xatolari, ya'ni field-level xatolari o'zgartirilmaydi)
            if isinstance(response.data, dict) and list(response.data.keys()) == ['detail']:
                method = context.get('request').method if context.get('request') else ''
                response.data['detail'] = uzbek_msg.format(method=method)

    return response
