"""
============================================================
DASHBOARD — View
============================================================
Endpoint:
  GET /api/v1/dashboard/

Parametrlar:
  date_from   — YYYY-MM-DD  (default: bu oyning 1-kuni)
  date_to     — YYYY-MM-DD  (default: bugun)
  branch      — Branch ID   (ixtiyoriy, yo'q bo'lsa barcha filiallar)
  limit       — int         (top mahsulotlar soni, default: 10)

Kesh:
  Redis, TTL = 5 daqiqa
  Kalit: dashboard_{store_id}_{branch}_{date_from}_{date_to}_{limit}

Ruxsat:
  IsAuthenticated (barcha xodimlar ko'rishi mumkin)
"""

import logging
from datetime import date

from django.core.cache import cache
from django.utils.dateparse import parse_date

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .utils import (
    calc_branches,
    calc_chart_data,
    calc_current_smena,
    calc_customers,
    calc_expenses,
    calc_products,
    calc_sales,
    calc_suppliers,
)

logger = logging.getLogger(__name__)

_CACHE_TTL = 300  # 5 daqiqa


class DashboardView(APIView):
    """
    GET /api/v1/dashboard/

    Javob tuzilmasi:
      period         — filtrlangan davr ma'lumoti
      sales          — savdo statistikasi + oldingi davr
      products       — top sotilganlar, top foydalilar, kam qoldiq
      customers      — jami, yangi, top xaridorlar, nasiya
      expenses       — jami, kategoriya bo'yicha, xarajat/tushum %
      suppliers      — jami qarz, top qarzdorlar
      branches       — har filial sotuvi
      current_smena  — ochiq smenalar holati
      chart_data     — kunlik sotuv, to'lov taqsimoti, soatlik heatmap
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        worker   = request.user.worker
        store_id = worker.store_id

        # ---- Parametrlarni tahlil qilish ----
        today     = date.today()
        d_from_str = request.query_params.get('date_from')
        d_to_str   = request.query_params.get('date_to')
        branch_id  = request.query_params.get('branch') or None
        try:
            limit  = max(1, min(50, int(request.query_params.get('limit', 10))))
        except (ValueError, TypeError):
            limit  = 10

        date_from = parse_date(d_from_str) if d_from_str else today.replace(day=1)
        date_to   = parse_date(d_to_str)   if d_to_str   else today

        # Sana validatsiyasi
        if not date_from or not date_to or date_from > date_to:
            date_from = today.replace(day=1)
            date_to   = today

        if branch_id:
            try:
                branch_id = int(branch_id)
            except (ValueError, TypeError):
                branch_id = None

        # ---- Kesh kaliti ----
        cache_key = (
            f"dashboard_{store_id}_{branch_id}_"
            f"{date_from}_{date_to}_{limit}"
        )

        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        # ---- Hisoblash ----
        try:
            data = {
                'period': {
                    'date_from':   str(date_from),
                    'date_to':     str(date_to),
                    'branch_id':   branch_id,
                    'days':        (date_to - date_from).days + 1,
                },
                'sales':         calc_sales(store_id, date_from, date_to, branch_id),
                'products':      calc_products(store_id, date_from, date_to, branch_id, limit),
                'customers':     calc_customers(store_id, date_from, date_to, branch_id),
                'expenses':      calc_expenses(store_id, date_from, date_to, branch_id),
                'suppliers':     calc_suppliers(store_id),
                'branches':      calc_branches(store_id, date_from, date_to),
                'current_smena': calc_current_smena(store_id, branch_id),
                'chart_data':    calc_chart_data(store_id, date_from, date_to, branch_id),
            }
        except Exception as exc:
            logger.exception("Dashboard hisoblashda xato: store_id=%s", store_id)
            return Response(
                {'detail': 'Dashboard ma\'lumotlarini yuklashda xato yuz berdi.'},
                status=500,
            )

        # ---- Keshga yozish ----
        cache.set(cache_key, data, timeout=_CACHE_TTL)

        return Response(data)
