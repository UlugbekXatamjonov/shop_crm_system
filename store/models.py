"""
============================================================
STORE APP — Modellar (Vaqtinchalik — 1-bosqich)
============================================================
Bu fayl hozircha faqat accaunt app uchun zarur bo'lgan
Store va Branch modellarini o'z ichiga oladi.

KEYINGI BOSQICHDA (2-bosqich — Stores) bu fayl to'liq yoziladi:
  Store, Branch, Warehouse, StoreSettings,
  SubscriptionPlan, Subscription, Payment,
  Coupon, CouponUsage, ExchangeRate
"""

from django.db import models


class Store(models.Model):
    """
    Do'kon modeli.
    Hozircha faqat name maydoni bor.
    Keyingi bosqichda kengaytiriladi.
    """
    name = models.CharField(
        max_length=200,
        verbose_name="Do'kon nomi"
    )

    class Meta:
        verbose_name = "Do'kon"
        verbose_name_plural = "Do'konlar"

    def __str__(self) -> str:
        return self.name


class Branch(models.Model):
    """
    Filial modeli.
    Hozircha faqat name maydoni bor.
    Keyingi bosqichda kengaytiriladi.
    """
    name = models.CharField(
        max_length=200,
        verbose_name="Filial nomi"
    )

    class Meta:
        verbose_name = 'Filial'
        verbose_name_plural = 'Filiallar'

    def __str__(self) -> str:
        return self.name
