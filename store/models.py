"""
============================================================
STORE APP — Modellar
============================================================
Modellar:
  StoreStatus — Do'kon va filial holatlari (TextChoices)
  Store       — Do'kon
  Branch      — Filial (do'konga biriktirilgan)
"""

from django.db import models


# ============================================================
# STATUS CHOICES
# ============================================================

class StoreStatus(models.TextChoices):
    ACTIVE   = 'active',   'Faol'
    INACTIVE = 'inactive', 'Nofaol'


# ============================================================
# DO'KON MODELI
# ============================================================

class Store(models.Model):
    """
    Do'kon modeli.
    Har bir do'konning o'ziga xos xodimlari va filiallari bo'ladi.
    """
    name       = models.CharField(
        max_length=200,
        verbose_name="Do'kon nomi"
    )
    address    = models.CharField(
        max_length=300,
        blank=True,
        verbose_name="Manzil"
    )
    phone      = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="Telefon"
    )
    status     = models.CharField(
        max_length=10,
        choices=StoreStatus.choices,
        default=StoreStatus.ACTIVE,
        verbose_name="Holati"
    )
    created_on = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Yaratilgan vaqti"
    )

    class Meta:
        verbose_name        = "Do'kon"
        verbose_name_plural = "Do'konlar"
        ordering            = ['-created_on']

    def __str__(self) -> str:
        return self.name


# ============================================================
# FILIAL MODELI
# ============================================================

class Branch(models.Model):
    """
    Filial modeli.
    Har bir filial bitta do'konga tegishli.
    Xodimlar filialga biriktiriladi.
    """
    store      = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name='branches',
        null=True,
        blank=True,
        verbose_name="Do'koni"
    )
    name       = models.CharField(
        max_length=200,
        verbose_name="Filial nomi"
    )
    address    = models.CharField(
        max_length=300,
        blank=True,
        verbose_name="Manzil"
    )
    phone      = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="Telefon"
    )
    status     = models.CharField(
        max_length=10,
        choices=StoreStatus.choices,
        default=StoreStatus.ACTIVE,
        verbose_name="Holati"
    )
    created_on = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Yaratilgan vaqti"
    )

    class Meta:
        verbose_name        = 'Filial'
        verbose_name_plural = 'Filiallar'
        ordering            = ['-created_on']

    def __str__(self) -> str:
        return f"{self.name} ({self.store.name if self.store else '—'})"
