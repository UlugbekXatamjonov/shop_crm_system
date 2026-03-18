"""
============================================================
DASHBOARD — Hisoblash funksiyalari
============================================================
Har bir funksiya bitta bo'lim uchun hisob-kitob qiladi va
dict qaytaradi. views.py da yig'iladi + Redis keshga yoziladi.

Foyda (profit) = SaleItem.total_price − (SaleItem.unit_cost × quantity)
  unit_cost NULL bo'lsa — FIFO tannarx yo'q, foyda hisoblanmaydi (None).
"""

from datetime import date, timedelta
from decimal import Decimal

from django.db.models import (
    Case,
    Count,
    DecimalField,
    ExpressionWrapper,
    F,
    FloatField,
    Q,
    Sum,
    Value,
    When,
)
from django.db.models.functions import (
    ExtractHour,
    TruncDate,
    TruncDay,
)
from django.utils import timezone

from expense.models import Expense
from store.models import Branch, Smena, SmenaStatus
from trade.models import Customer, Sale, SaleItem, SaleStatus
from warehouse.models import Product, Stock, Supplier


# ============================================================
# YORDAMCHI
# ============================================================

def _prev_period(date_from: date, date_to: date) -> tuple[date, date]:
    """Bir xil uzunlikdagi oldingi davr."""
    delta     = (date_to - date_from) + timedelta(days=1)
    prev_to   = date_from - timedelta(days=1)
    prev_from = prev_to - delta + timedelta(days=1)
    return prev_from, prev_to


def _pct_change(current: Decimal, previous: Decimal) -> float | None:
    """Foizli o'zgarish. previous = 0 bo'lsa None."""
    if not previous:
        return None
    return round(float((current - previous) / previous * 100), 2)


def _d(val) -> float:
    """Decimal → float (JSON uchun)."""
    if val is None:
        return 0.0
    return round(float(val), 2)


# ============================================================
# 1. SAVDO BO'LIMI
# ============================================================

def calc_sales(store_id: int, date_from: date, date_to: date, branch_id=None) -> dict:
    """Savdo statistikasi + oldingi davr bilan taqqoslash."""

    def _qs(d_from, d_to):
        qs = Sale.objects.filter(
            store_id=store_id,
            status=SaleStatus.COMPLETED,
            created_on__date__gte=d_from,
            created_on__date__lte=d_to,
        )
        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        return qs

    def _agg(qs):
        agg = qs.aggregate(
            revenue=Sum('total_price'),
            discount=Sum('discount_amount'),
            cash=Sum('cash_amount'),
            card=Sum('card_amount'),
            debt=Sum('debt_amount'),
            count=Count('id'),
        )
        revenue  = agg['revenue']  or Decimal('0')
        discount = agg['discount'] or Decimal('0')
        count    = agg['count']    or 0
        net_rev  = revenue - discount
        return {
            'revenue':         net_rev,
            'gross_revenue':   revenue,
            'discount_total':  discount,
            'cash_total':      agg['cash'] or Decimal('0'),
            'card_total':      agg['card'] or Decimal('0'),
            'debt_total':      agg['debt'] or Decimal('0'),
            'count':           count,
            'avg_check':       (net_rev / count) if count else Decimal('0'),
        }

    # Joriy davr
    cur_qs  = _qs(date_from, date_to)
    cur     = _agg(cur_qs)

    # Foyda — SaleItem orqali
    item_qs = SaleItem.objects.filter(
        sale__store_id=store_id,
        sale__status=SaleStatus.COMPLETED,
        sale__created_on__date__gte=date_from,
        sale__created_on__date__lte=date_to,
    )
    if branch_id:
        item_qs = item_qs.filter(sale__branch_id=branch_id)

    profit_agg = item_qs.aggregate(
        total_revenue=Sum('total_price'),
        total_cost=Sum(
            ExpressionWrapper(
                F('unit_cost') * F('quantity'),
                output_field=DecimalField(),
            ),
            filter=Q(unit_cost__isnull=False),
        ),
    )
    profit_revenue = profit_agg['total_revenue'] or Decimal('0')
    profit_cost    = profit_agg['total_cost']    or Decimal('0')
    profit         = profit_revenue - profit_cost
    margin_pct     = _d(profit / profit_revenue * 100) if profit_revenue else 0.0

    # Oldingi davr
    prev_from, prev_to = _prev_period(date_from, date_to)
    prev_qs = _qs(prev_from, prev_to)
    prev    = _agg(prev_qs)

    return {
        'total_revenue':      _d(cur['revenue']),
        'gross_revenue':      _d(cur['gross_revenue']),
        'discount_total':     _d(cur['discount_total']),
        'cash_total':         _d(cur['cash_total']),
        'card_total':         _d(cur['card_total']),
        'debt_total':         _d(cur['debt_total']),
        'count':              cur['count'],
        'avg_check':          _d(cur['avg_check']),
        'total_profit':       _d(profit),
        'margin_percent':     margin_pct,
        'vs_prev_period': {
            'revenue':        _d(prev['revenue']),
            'count':          prev['count'],
            'revenue_diff':   _d(cur['revenue'] - prev['revenue']),
            'revenue_pct':    _pct_change(cur['revenue'], prev['revenue']),
            'count_diff':     cur['count'] - prev['count'],
        },
    }


# ============================================================
# 2. MAHSULOT BO'LIMI
# ============================================================

def calc_products(store_id: int, date_from: date, date_to: date, branch_id=None, limit=10) -> dict:
    """Top sotilganlar, top foydalilar, kam qoldiq, ombor qiymati."""

    item_filter = Q(
        sale__store_id=store_id,
        sale__status=SaleStatus.COMPLETED,
        sale__created_on__date__gte=date_from,
        sale__created_on__date__lte=date_to,
    )
    if branch_id:
        item_filter &= Q(sale__branch_id=branch_id)

    # Top sotilganlar (miqdor bo'yicha)
    top_selling = (
        SaleItem.objects
        .filter(item_filter)
        .values('product_id', 'product__name', 'product__unit')
        .annotate(
            total_qty=Sum('quantity'),
            total_rev=Sum('total_price'),
        )
        .order_by('-total_qty')[:limit]
    )

    # Top foydalilar (foyda summasi bo'yicha)
    top_profitable = (
        SaleItem.objects
        .filter(item_filter, unit_cost__isnull=False)
        .values('product_id', 'product__name', 'product__unit')
        .annotate(
            total_profit=Sum(
                ExpressionWrapper(
                    F('total_price') - F('unit_cost') * F('quantity'),
                    output_field=DecimalField(),
                )
            ),
            total_rev=Sum('total_price'),
        )
        .order_by('-total_profit')[:limit]
    )

    # Kam qoldiq
    stock_filter = Q(product__store_id=store_id)
    if branch_id:
        stock_filter &= Q(branch_id=branch_id)

    from config.cache_utils import get_store_settings
    settings = get_store_settings(store_id)
    threshold = settings.low_stock_threshold if settings.low_stock_enabled else 0

    low_stock_qs = (
        Stock.objects
        .filter(stock_filter, quantity__lte=threshold, quantity__gt=0)
        .select_related('product', 'branch', 'warehouse')
        .order_by('quantity')
    )
    low_stock_count = low_stock_qs.count()
    low_stock = low_stock_qs[:20]

    # Ombor umumiy qiymati (qoldiq × tannarx)
    warehouse_value = (
        Stock.objects
        .filter(stock_filter, quantity__gt=0)
        .aggregate(
            val=Sum(
                ExpressionWrapper(
                    F('quantity') * F('product__purchase_price'),
                    output_field=DecimalField(),
                )
            )
        )['val'] or Decimal('0')
    )

    return {
        'top_selling': [
            {
                'product_id':   r['product_id'],
                'name':         r['product__name'],
                'unit':         r['product__unit'],
                'total_qty':    _d(r['total_qty']),
                'total_revenue':_d(r['total_rev']),
            }
            for r in top_selling
        ],
        'top_profitable': [
            {
                'product_id':   r['product_id'],
                'name':         r['product__name'],
                'unit':         r['product__unit'],
                'total_profit': _d(r['total_profit']),
                'total_revenue':_d(r['total_rev']),
            }
            for r in top_profitable
        ],
        'low_stock': [
            {
                'product_id':   s.product_id,
                'name':         s.product.name,
                'quantity':     _d(s.quantity),
                'unit':         s.product.unit,
                'location':     s.branch.name if s.branch_id else s.warehouse.name,
                'location_type':'branch' if s.branch_id else 'warehouse',
            }
            for s in low_stock
        ],
        'low_stock_count':   low_stock_count,
        'warehouse_value':   _d(warehouse_value),
    }


# ============================================================
# 3. MIJOZ BO'LIMI
# ============================================================

def calc_customers(store_id: int, date_from: date, date_to: date, branch_id=None) -> dict:
    base_filter = Q(store_id=store_id)
    if branch_id:
        base_filter &= Q(sales__branch_id=branch_id)

    total = Customer.objects.filter(store_id=store_id, status='active').count()
    new   = Customer.objects.filter(
        store_id=store_id,
        created_on__date__gte=date_from,
        created_on__date__lte=date_to,
    ).count()

    # Jami nasiya qoldig'i
    total_debt = (
        Customer.objects
        .filter(store_id=store_id, status='active', debt_balance__gt=0)
        .aggregate(s=Sum('debt_balance'))['s'] or Decimal('0')
    )

    # Top xaridorlar (davr ichida)
    sale_filter = Q(
        store_id=store_id,
        status=SaleStatus.COMPLETED,
        created_on__date__gte=date_from,
        created_on__date__lte=date_to,
        customer__isnull=False,
    )
    if branch_id:
        sale_filter &= Q(branch_id=branch_id)

    top_buyers = (
        Sale.objects
        .filter(sale_filter)
        .values('customer_id', 'customer__name')
        .annotate(
            total_spent=Sum(ExpressionWrapper(
                F('total_price') - F('discount_amount'),
                output_field=DecimalField(),
            )),
            visit_count=Count('id'),
        )
        .order_by('-total_spent')[:5]
    )

    return {
        'total':       total,
        'new_count':   new,
        'total_debt':  _d(total_debt),
        'top_buyers': [
            {
                'customer_id':  r['customer_id'],
                'name':         r['customer__name'],
                'total_spent':  _d(r['total_spent']),
                'visit_count':  r['visit_count'],
            }
            for r in top_buyers
        ],
    }


# ============================================================
# 4. XARAJAT BO'LIMI
# ============================================================

def calc_expenses(store_id: int, date_from: date, date_to: date, branch_id=None) -> dict:
    qs = Expense.objects.filter(
        store_id=store_id,
        date__gte=date_from,
        date__lte=date_to,
    )
    if branch_id:
        qs = qs.filter(branch_id=branch_id)

    total = qs.aggregate(s=Sum('amount'))['s'] or Decimal('0')

    by_category = (
        qs
        .values('category_id', 'category__name')
        .annotate(total=Sum('amount'))
        .order_by('-total')
    )

    # Davr ichida tushum
    sale_rev = Sale.objects.filter(
        store_id=store_id,
        status=SaleStatus.COMPLETED,
        created_on__date__gte=date_from,
        created_on__date__lte=date_to,
    )
    if branch_id:
        sale_rev = sale_rev.filter(branch_id=branch_id)
    revenue = sale_rev.aggregate(
        s=Sum(ExpressionWrapper(
            F('total_price') - F('discount_amount'),
            output_field=DecimalField(),
        ))
    )['s'] or Decimal('0')
    expense_ratio = _d(total / revenue * 100) if revenue else 0.0

    return {
        'total':         _d(total),
        'expense_ratio': expense_ratio,
        'by_category': [
            {
                'category_id': r['category_id'],
                'name':        r['category__name'] or 'Kategoriyasiz',
                'total':       _d(r['total']),
                'percent':     _d(r['total'] / total * 100) if total else 0.0,
            }
            for r in by_category
        ],
    }


# ============================================================
# 5. YETKAZIB BERUVCHI BO'LIMI
# ============================================================

def calc_suppliers(store_id: int) -> dict:
    qs = Supplier.objects.filter(store_id=store_id, status='active')

    total_debt = qs.aggregate(s=Sum('debt_balance'))['s'] or Decimal('0')

    top_debtors = qs.filter(debt_balance__gt=0).order_by('-debt_balance')[:5]

    return {
        'total_debt': _d(total_debt),
        'top_debtors': [
            {
                'supplier_id': s.id,
                'name':        s.name,
                'company':     s.company,
                'debt_balance':_d(s.debt_balance),
            }
            for s in top_debtors
        ],
    }


# ============================================================
# 6. FILIAL BO'LIMI
# ============================================================

def calc_branches(store_id: int, date_from: date, date_to: date) -> list:
    """Har bir filial bo'yicha sotuv yig'indisi (bitta query)."""
    branches = Branch.objects.filter(store_id=store_id, status='active')
    branch_map = {b.id: b.name for b in branches}

    if not branch_map:
        return []

    # Barcha filiallar uchun bitta query
    agg_qs = (
        Sale.objects
        .filter(
            store_id=store_id,
            branch_id__in=branch_map.keys(),
            status=SaleStatus.COMPLETED,
            created_on__date__gte=date_from,
            created_on__date__lte=date_to,
        )
        .values('branch_id')
        .annotate(
            revenue=Sum(ExpressionWrapper(
                F('total_price') - F('discount_amount'),
                output_field=DecimalField(),
            )),
            count=Count('id'),
        )
    )
    agg_map = {r['branch_id']: r for r in agg_qs}

    result = []
    for branch_id, name in branch_map.items():
        data = agg_map.get(branch_id, {})
        result.append({
            'branch_id': branch_id,
            'name':      name,
            'revenue':   _d(data.get('revenue') or 0),
            'count':     data.get('count') or 0,
        })

    # Tushum bo'yicha tartiblash
    result.sort(key=lambda x: x['revenue'], reverse=True)
    return result


# ============================================================
# 7. JORIY SMENA
# ============================================================

def calc_current_smena(store_id: int, branch_id=None) -> dict:
    """Ochiq smena(lar) holati (bitta query)."""
    qs = Smena.objects.filter(
        store_id=store_id,
        status=SmenaStatus.OPEN,
    ).select_related('branch', 'worker_open')
    if branch_id:
        qs = qs.filter(branch_id=branch_id)

    smena_list = list(qs)
    smena_ids = [s.id for s in smena_list]

    # Barcha ochiq smenalar uchun bitta query
    sales_agg = {}
    if smena_ids:
        sales_agg = {
            r['smena_id']: r
            for r in (
                Sale.objects
                .filter(smena_id__in=smena_ids, status=SaleStatus.COMPLETED)
                .values('smena_id')
                .annotate(
                    count=Count('id'),
                    revenue=Sum(ExpressionWrapper(
                        F('total_price') - F('discount_amount'),
                        output_field=DecimalField(),
                    )),
                )
            )
        }

    open_smenas = []
    for smena in smena_list:
        data = sales_agg.get(smena.id, {})
        open_smenas.append({
            'smena_id':    smena.id,
            'branch':      smena.branch.name,
            'worker':      smena.worker_open.get_full_name() if smena.worker_open_id else '',
            'start_time':  smena.start_time.strftime('%d.%m.%Y %H:%M') if smena.start_time else '',
            'sales_count': data.get('count') or 0,
            'sales_total': _d(data.get('revenue') or 0),
        })

    return {
        'open_count': len(open_smenas),
        'smenas':     open_smenas,
    }


# ============================================================
# 8. GRAFIK MA'LUMOTLAR
# ============================================================

def calc_chart_data(store_id: int, date_from: date, date_to: date, branch_id=None) -> dict:
    """
    daily_sales    — har kun uchun tushum
    payment_breakdown — to'lov turi taqsimoti
    hourly_heatmap — soat bo'yicha sotuv soni
    """
    sale_filter = Q(
        store_id=store_id,
        status=SaleStatus.COMPLETED,
        created_on__date__gte=date_from,
        created_on__date__lte=date_to,
    )
    if branch_id:
        sale_filter &= Q(branch_id=branch_id)

    # 1. Kunlik sotuv
    daily = (
        Sale.objects
        .filter(sale_filter)
        .annotate(day=TruncDate('created_on'))
        .values('day')
        .annotate(
            revenue=Sum(ExpressionWrapper(
                F('total_price') - F('discount_amount'),
                output_field=DecimalField(),
            )),
            count=Count('id'),
        )
        .order_by('day')
    )

    # Barcha kun uchun 0 bilan to'ldirish
    daily_map = {
        r['day']: {'revenue': _d(r['revenue']), 'count': r['count']}
        for r in daily
    }
    daily_sales = []
    cur = date_from
    while cur <= date_to:
        daily_sales.append({
            'date':    cur.strftime('%Y-%m-%d'),
            'revenue': daily_map.get(cur, {}).get('revenue', 0.0),
            'count':   daily_map.get(cur, {}).get('count', 0),
        })
        cur += timedelta(days=1)

    # 2. To'lov turi taqsimoti
    pay_agg = Sale.objects.filter(sale_filter).aggregate(
        cash=Sum('cash_amount'),
        card=Sum('card_amount'),
        debt=Sum('debt_amount'),
    )
    cash = _d(pay_agg['cash'] or 0)
    card = _d(pay_agg['card'] or 0)
    debt = _d(pay_agg['debt'] or 0)
    total_pay = cash + card + debt
    payment_breakdown = {
        'cash': {'amount': cash, 'percent': round(cash / total_pay * 100, 1) if total_pay else 0},
        'card': {'amount': card, 'percent': round(card / total_pay * 100, 1) if total_pay else 0},
        'debt': {'amount': debt, 'percent': round(debt / total_pay * 100, 1) if total_pay else 0},
    }

    # 3. Soatlik heatmap (0–23 soat)
    hourly = (
        Sale.objects
        .filter(sale_filter)
        .annotate(hour=ExtractHour('created_on'))
        .values('hour')
        .annotate(count=Count('id'))
        .order_by('hour')
    )
    hourly_map = {r['hour']: r['count'] for r in hourly}
    hourly_heatmap = [
        {'hour': h, 'count': hourly_map.get(h, 0)}
        for h in range(24)
    ]

    return {
        'daily_sales':        daily_sales,
        'payment_breakdown':  payment_breakdown,
        'hourly_heatmap':     hourly_heatmap,
    }
