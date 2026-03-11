"""
============================================================
EXPENSE APP — Modellar
============================================================
Modellar:
  ExpenseCategory — Xarajat kategoriyasi (multi-tenant, soft delete)
  Expense         — Xarajat yozuvi (kategoriya, filial, xodim, smena)

Multi-tenant: barcha modellar store(FK) orqali ajratilgan.

Bog'liqliklar:
  Expense.category(FK → ExpenseCategory)
  Expense.branch(FK → store.Branch)
  Expense.worker(FK → accaunt.Worker)
  Expense.smena(FK → store.Smena, ixtiyoriy)

→ smena yopilganda (Z-report) xarajatlar ham hisobga olinadi
→ Ruxsatlar: CanAccess('xarajatlar')
"""

from django.db import models

from warehouse.models import ActiveStatus


# ============================================================
# XARAJAT KATEGORIYASI
# ============================================================

class ExpenseCategory(models.Model):
    """
    Xarajat kategoriyasi.
    Har bir kategoriya bitta do'konga tegishli (multi-tenant).
    Soft delete — status='inactive' ga o'tkaziladi.

    Misol: Ijara, Kommunal, Maosh, Iste'mol, Boshqa.
    """
    name       = models.CharField(
        max_length=200,
        verbose_name='Nomi',
    )
    store      = models.ForeignKey(
        'store.Store',
        on_delete=models.CASCADE,
        related_name='expense_categories',
        verbose_name="Do'kon",
    )
    status     = models.CharField(
        max_length=10,
        choices=ActiveStatus.choices,
        default=ActiveStatus.ACTIVE,
        verbose_name='Holat',
    )
    created_on = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Yaratilgan vaqti',
    )

    class Meta:
        verbose_name        = 'Xarajat kategoriyasi'
        verbose_name_plural = 'Xarajat kategoriyalari'
        ordering            = ['name']
        unique_together     = [('store', 'name')]

    def __str__(self) -> str:
        return self.name


# ============================================================
# XARAJAT
# ============================================================

class Expense(models.Model):
    """
    Xarajat yozuvi.

    amount      — xarajat summasi (UZS)
    date        — xarajat sanasi (default: bugun)
    description — qo'shimcha izoh (ixtiyoriy)
    receipt_image — kvitansiya rasmi (ixtiyoriy, upload_to='expenses/')

    ⚠️ Xarajatlar o'chirilmaydi (soft delete yo'q, hard delete mavjud).
    ⚠️ Yopilgan smena xarajatlari Z-report da ko'rsatiladi.
    """
    category      = models.ForeignKey(
        ExpenseCategory,
        on_delete=models.PROTECT,
        related_name='expenses',
        verbose_name='Kategoriya',
    )
    branch        = models.ForeignKey(
        'store.Branch',
        on_delete=models.PROTECT,
        related_name='expenses',
        verbose_name='Filial',
    )
    store         = models.ForeignKey(
        'store.Store',
        on_delete=models.PROTECT,
        related_name='expenses',
        verbose_name="Do'kon",
    )
    worker        = models.ForeignKey(
        'accaunt.Worker',
        on_delete=models.PROTECT,
        related_name='expenses',
        verbose_name='Xodim',
    )
    smena         = models.ForeignKey(
        'store.Smena',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='expenses',
        verbose_name='Smena',
    )
    amount        = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name='Summa (so\'m)',
    )
    description   = models.TextField(
        blank=True,
        verbose_name='Izoh',
    )
    date          = models.DateField(
        verbose_name='Sana',
    )
    receipt_image = models.ImageField(
        upload_to='expenses/',
        null=True,
        blank=True,
        verbose_name='Kvitansiya rasmi',
    )
    created_on    = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Yaratilgan vaqti',
    )

    class Meta:
        verbose_name        = 'Xarajat'
        verbose_name_plural = 'Xarajatlar'
        ordering            = ['-date', '-created_on']

    def __str__(self) -> str:
        return f"{self.category.name} — {self.amount} so'm ({self.date})"
