"""
============================================================
EXPORT APP — View'lar
============================================================
Export (yuklab olish):
  SaleExportView          GET /api/v1/export/sales/
  ExpenseExportView       GET /api/v1/export/expenses/
  StockExportView         GET /api/v1/export/stocks/
  StockMovementExportView GET /api/v1/export/stock-movements/
  SupplierExportView      GET /api/v1/export/suppliers/

Import (shablon + yuklash):
  ProductImportView       GET  /api/v1/export/products/template/
                          POST /api/v1/export/products/import/
  CustomerImportView      GET  /api/v1/export/customers/template/
                          POST /api/v1/export/customers/import/
  StockMovementImportView GET  /api/v1/export/stock-movements/template/
                          POST /api/v1/export/stock-movements/import/
  SupplierImportView      GET  /api/v1/export/suppliers/template/
                          POST /api/v1/export/suppliers/import/
  SubCategoryImportView   GET  /api/v1/export/subcategories/template/
                          POST /api/v1/export/subcategories/import/

Ruxsatlar:
  Export — IsAuthenticated (barcha xodimlar ko'ra oladi)
  Import — IsManagerOrAbove (faqat menejer va yuqori)

Filtrlar (export):
  date_from, date_to  — YYYY-MM-DD formatda
  branch              — Branch ID
  smena               — Smena ID
  warehouse           — Warehouse ID
  movement_type       — in | out
  status              — model holatiga qarab
  format              — excel (default) | pdf
"""

from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils.dateparse import parse_date

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from accaunt.permissions import IsManagerOrAbove, SubscriptionRequired

from expense.models import Expense, ExpenseCategory
from store.models import Branch
from trade.models import Customer, CustomerGroup, Sale
from warehouse.models import (
    Category,
    MovementType,
    Product,
    ProductUnit,
    Stock,
    StockMovement,
    SubCategory,
    Supplier,
    Warehouse,
)

from .utils.excel import make_excel_response, make_template, parse_excel_upload
from .utils.pdf import make_pdf_response


# ============================================================
# YORDAMCHI FUNKSIYALAR
# ============================================================

def _get_format(request) -> str:
    """?format=excel|pdf  (default: excel)"""
    return request.query_params.get('format', 'excel').lower()


def _filter_date(qs, field: str, request):
    """date_from / date_to ni queryset ga qo'llash."""
    date_from = request.query_params.get('date_from')
    date_to   = request.query_params.get('date_to')
    if date_from:
        d = parse_date(date_from)
        if d:
            qs = qs.filter(**{f'{field}__date__gte': d})
    if date_to:
        d = parse_date(date_to)
        if d:
            qs = qs.filter(**{f'{field}__date__lte': d})
    return qs


def _to_decimal(val: str) -> Decimal | None:
    """Stringdan Decimal olish, xato bo'lsa None."""
    try:
        return Decimal(str(val).replace(',', '.'))
    except (InvalidOperation, ValueError):
        return None


def _fmt_dt(dt) -> str:
    """DateTimeField → ko'rinadigan matn."""
    if dt is None:
        return ''
    return dt.strftime('%d.%m.%Y %H:%M')


def _fmt_d(d) -> str:
    """DateField → ko'rinadigan matn."""
    if d is None:
        return ''
    return d.strftime('%d.%m.%Y') if hasattr(d, 'strftime') else str(d)


# ============================================================
# EXPORT VIEWS
# ============================================================

class SaleExportView(APIView):
    """
    GET /api/v1/export/sales/
    Filtrlar: format, date_from, date_to, branch, smena, status
    """
    permission_classes = [IsAuthenticated, SubscriptionRequired('has_export')]

    def get(self, request):
        worker = request.user.worker
        qs = (
            Sale.objects
            .filter(store=worker.store)
            .select_related('branch', 'worker__user', 'customer', 'smena')
            .prefetch_related('items__product')
        )

        # Filtrlar
        qs = _filter_date(qs, 'created_on', request)
        branch = request.query_params.get('branch')
        smena  = request.query_params.get('smena')
        st     = request.query_params.get('status')
        if branch: qs = qs.filter(branch_id=branch)
        if smena:  qs = qs.filter(smena_id=smena)
        if st:     qs = qs.filter(status=st)

        headers = [
            '#', 'Sana', 'Filial', 'Kassir', 'Mijoz',
            'To\'lov turi', 'Jami summa', 'Chegirma', 'Naqd',
            'Karta', 'Nasiya', 'Holat', 'Smena',
        ]
        rows = []
        for i, sale in enumerate(qs, start=1):
            is_cash = sale.payment_type == 'cash'
            is_card = sale.payment_type == 'card'
            rows.append([
                i,
                _fmt_dt(sale.created_on),
                sale.branch.name if sale.branch else '',
                sale.worker.user.get_full_name() if sale.worker else '',
                sale.customer.name if sale.customer_id else '',
                sale.get_payment_type_display(),
                float(sale.total_price),
                float(sale.discount_amount),
                float(sale.paid_amount) if is_cash else 0.0,
                float(sale.paid_amount) if is_card else 0.0,
                float(sale.debt_amount),
                sale.get_status_display(),
                f'#{sale.smena_id}' if sale.smena_id else '',
            ])

        fmt = _get_format(request)
        if fmt == 'pdf':
            return make_pdf_response(
                filename='sotuvlar.pdf',
                title='Sotuvlar hisoboti',
                headers=headers,
                rows=rows,
                landscape_mode=True,
            )
        return make_excel_response('sotuvlar.xlsx', headers, rows)


class ExpenseExportView(APIView):
    """
    GET /api/v1/export/expenses/
    Filtrlar: format, date_from, date_to, branch, smena, category
    """
    permission_classes = [IsAuthenticated, SubscriptionRequired('has_export')]

    def get(self, request):
        worker = request.user.worker
        qs = (
            Expense.objects
            .filter(store=worker.store)
            .select_related('branch', 'worker__user', 'category', 'smena')
        )

        qs = _filter_date(qs, 'date', request)
        branch   = request.query_params.get('branch')
        smena    = request.query_params.get('smena')
        category = request.query_params.get('category')
        if branch:   qs = qs.filter(branch_id=branch)
        if smena:    qs = qs.filter(smena_id=smena)
        if category: qs = qs.filter(category_id=category)

        headers = [
            '#', 'Sana', 'Kategoriya', 'Filial', 'Xodim',
            'Summa', 'Izoh', 'Smena',
        ]
        rows = []
        for i, exp in enumerate(qs, start=1):
            rows.append([
                i,
                _fmt_d(exp.date),
                exp.category.name if exp.category_id else '',
                exp.branch.name if exp.branch_id else '',
                exp.worker.user.get_full_name() if exp.worker_id else '',
                float(exp.amount),
                exp.description,
                f'#{exp.smena_id}' if exp.smena_id else '',
            ])

        fmt = _get_format(request)
        if fmt == 'pdf':
            return make_pdf_response(
                filename='xarajatlar.pdf',
                title='Xarajatlar hisoboti',
                headers=headers,
                rows=rows,
            )
        return make_excel_response('xarajatlar.xlsx', headers, rows)


class StockExportView(APIView):
    """
    GET /api/v1/export/stocks/
    Filtrlar: branch, warehouse
    Format: faqat excel (qoldig' PDF uchun foydali emas)
    """
    permission_classes = [IsAuthenticated, SubscriptionRequired('has_export')]

    def get(self, request):
        worker = request.user.worker
        qs = (
            Stock.objects
            .filter(product__store=worker.store)
            .select_related('product__category', 'product__subcategory', 'branch', 'warehouse')
        )

        branch    = request.query_params.get('branch')
        warehouse = request.query_params.get('warehouse')
        if branch:    qs = qs.filter(branch_id=branch)
        if warehouse: qs = qs.filter(warehouse_id=warehouse)

        headers = [
            '#', 'Mahsulot', 'Kategoriya', 'Subkategoriya',
            'Birlik', 'Qoldiq', 'Joylashuv', 'Tur',
            'Sotish narxi', 'Xarid narxi',
        ]
        rows = []
        for i, stock in enumerate(qs, start=1):
            p   = stock.product
            loc = stock.branch.name if stock.branch_id else stock.warehouse.name
            typ = 'Filial' if stock.branch_id else 'Ombor'
            rows.append([
                i,
                p.name,
                p.category.name if p.category_id else '',
                p.subcategory.name if p.subcategory_id else '',
                p.get_unit_display(),
                float(stock.quantity),
                loc,
                typ,
                float(p.sale_price),
                float(p.purchase_price),
            ])

        return make_excel_response('qoldiqlar.xlsx', headers, rows)


class StockMovementExportView(APIView):
    """
    GET /api/v1/export/stock-movements/
    Filtrlar: format, date_from, date_to, branch, warehouse, movement_type
    """
    permission_classes = [IsAuthenticated, SubscriptionRequired('has_export')]

    def get(self, request):
        worker = request.user.worker
        qs = (
            StockMovement.objects
            .filter(product__store=worker.store)
            .select_related('product', 'branch', 'warehouse', 'worker__user', 'supplier')
        )

        qs = _filter_date(qs, 'created_on', request)
        branch    = request.query_params.get('branch')
        warehouse = request.query_params.get('warehouse')
        mv_type   = request.query_params.get('movement_type')
        if branch:    qs = qs.filter(branch_id=branch)
        if warehouse: qs = qs.filter(warehouse_id=warehouse)
        if mv_type:   qs = qs.filter(movement_type=mv_type)

        headers = [
            '#', 'Sana', 'Harakat', 'Mahsulot',
            'Miqdor', 'Birlik', 'Tannarx', 'Joylashuv',
            'Xodim', 'Yetkazib beruvchi', 'Izoh',
        ]
        rows = []
        for i, mv in enumerate(qs, start=1):
            loc = mv.branch.name if mv.branch_id else mv.warehouse.name
            rows.append([
                i,
                _fmt_dt(mv.created_on),
                mv.get_movement_type_display(),
                mv.product.name,
                float(mv.quantity),
                mv.product.get_unit_display(),
                float(mv.unit_cost) if mv.unit_cost else '',
                loc,
                mv.worker.user.get_full_name() if mv.worker_id else '',
                mv.supplier.name if mv.supplier_id else '',
                mv.note,
            ])

        fmt = _get_format(request)
        if fmt == 'pdf':
            return make_pdf_response(
                filename='harakatlar.pdf',
                title='Ombor harakatlari hisoboti',
                headers=headers,
                rows=rows,
                landscape_mode=True,
            )
        return make_excel_response('harakatlar.xlsx', headers, rows)


class SupplierExportView(APIView):
    """
    GET /api/v1/export/suppliers/
    Filtrlar: format, status
    """
    permission_classes = [IsAuthenticated, SubscriptionRequired('has_export')]

    def get(self, request):
        worker = request.user.worker
        qs = Supplier.objects.filter(store=worker.store)

        st = request.query_params.get('status')
        if st: qs = qs.filter(status=st)

        headers = [
            '#', 'Nomi', 'Kompaniya', 'Telefon',
            'Manzil', 'Qarz balansi', 'Holat', 'Izoh',
        ]
        rows = []
        for i, sup in enumerate(qs, start=1):
            rows.append([
                i,
                sup.name,
                sup.company,
                sup.phone,
                sup.address,
                float(sup.debt_balance),
                sup.get_status_display(),
                sup.note,
            ])

        fmt = _get_format(request)
        if fmt == 'pdf':
            return make_pdf_response(
                filename='yetkazib_beruvchilar.pdf',
                title='Yetkazib beruvchilar',
                headers=headers,
                rows=rows,
            )
        return make_excel_response('yetkazib_beruvchilar.xlsx', headers, rows)


# ============================================================
# IMPORT VIEWS — Mahsulot
# ============================================================

PRODUCT_HEADERS = ['nom', 'kategoriya', 'subkategoriya', 'sale_price', 'purchase_price', 'birlik', 'barcode']
PRODUCT_NOTES = {
    'nom':           'Mahsulot nomi (majburiy)',
    'kategoriya':    'Mavjud kategoriya nomi (ixtiyoriy)',
    'subkategoriya': 'Mavjud subkategoriya nomi (ixtiyoriy)',
    'sale_price':    'Sotish narxi (majburiy, raqam)',
    'purchase_price':'Xarid narxi (ixtiyoriy, raqam)',
    'birlik':        'dona / kg / g / litr / metr / m2 / yashik / qop / quti',
    'barcode':       'Shtrix-kod (ixtiyoriy)',
}
VALID_UNITS = [u.value for u in ProductUnit]


class ProductImportView(APIView):
    permission_classes = [IsManagerOrAbove, SubscriptionRequired('has_export')]

    def get(self, request):
        """GET → bo'sh shablon .xlsx"""
        return make_template('mahsulotlar_shablon.xlsx', PRODUCT_HEADERS, PRODUCT_NOTES)

    def post(self, request):
        """POST → faylni yuklash va import qilish"""
        file = request.FILES.get('file')
        if not file:
            return Response({'detail': 'file maydoni kerak.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            rows = parse_excel_upload(file)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        worker = request.user.worker
        store  = worker.store

        # Kategoriya va subkategoriyalarni oldindan yuklash
        cats    = {c.name.lower(): c for c in Category.objects.filter(store=store)}
        subcats = {s.name.lower(): s for s in SubCategory.objects.filter(category__store=store)}

        created = 0
        skipped = 0
        errors  = []

        for row_num, row in enumerate(rows, start=2):
            nom = row.get('nom', '').strip()
            if not nom:
                errors.append({'row': row_num, 'error': 'nom maydoni bo\'sh.'})
                continue

            sale_price = _to_decimal(row.get('sale_price', ''))
            if sale_price is None:
                errors.append({'row': row_num, 'error': f'sale_price noto\'g\'ri: "{row.get("sale_price")}"'})
                continue

            purchase_price = _to_decimal(row.get('purchase_price', '') or '0') or Decimal('0')
            unit = row.get('birlik', 'dona').strip().lower()
            if unit not in VALID_UNITS:
                unit = 'dona'

            cat_name    = row.get('kategoriya', '').strip().lower()
            subcat_name = row.get('subkategoriya', '').strip().lower()
            barcode     = row.get('barcode', '').strip() or None

            category    = cats.get(cat_name)
            subcategory = subcats.get(subcat_name)

            # Bir do'konda bir xil nom bo'lmasligi kerak
            if Product.objects.filter(store=store, name=nom).exists():
                skipped += 1
                errors.append({'row': row_num, 'error': f'"{nom}" allaqachon mavjud — o\'tkazib yuborildi.'})
                continue

            try:
                with transaction.atomic():
                    Product.objects.create(
                        store=store,
                        name=nom,
                        category=category,
                        subcategory=subcategory,
                        sale_price=sale_price,
                        purchase_price=purchase_price,
                        unit=unit,
                        barcode=barcode or None,
                    )
                created += 1
            except Exception as e:
                errors.append({'row': row_num, 'error': str(e)})

        return Response({
            'created': created,
            'skipped': skipped,
            'errors':  errors,
        }, status=status.HTTP_200_OK)


# ============================================================
# IMPORT VIEWS — Mijoz
# ============================================================

CUSTOMER_HEADERS = ['ism', 'telefon', 'manzil', 'guruh', 'izoh']
CUSTOMER_NOTES = {
    'ism':    'Mijoz ismi (majburiy)',
    'telefon':'Telefon raqami (ixtiyoriy)',
    'manzil': 'Manzil (ixtiyoriy)',
    'guruh':  'Mavjud guruh nomi (ixtiyoriy)',
    'izoh':   'Izoh (ixtiyoriy)',
}


class CustomerImportView(APIView):
    permission_classes = [IsManagerOrAbove, SubscriptionRequired('has_export')]

    def get(self, request):
        return make_template('mijozlar_shablon.xlsx', CUSTOMER_HEADERS, CUSTOMER_NOTES)

    def post(self, request):
        file = request.FILES.get('file')
        if not file:
            return Response({'detail': 'file maydoni kerak.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            rows = parse_excel_upload(file)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        worker = request.user.worker
        store  = worker.store

        groups = {g.name.lower(): g for g in CustomerGroup.objects.filter(store=store)}

        created = 0
        skipped = 0
        errors  = []

        for row_num, row in enumerate(rows, start=2):
            ism = row.get('ism', '').strip()
            if not ism:
                errors.append({'row': row_num, 'error': 'ism maydoni bo\'sh.'})
                continue

            guruh_name = row.get('guruh', '').strip().lower()
            group      = groups.get(guruh_name)

            if Customer.objects.filter(store=store, name=ism).exists():
                skipped += 1
                errors.append({'row': row_num, 'error': f'"{ism}" allaqachon mavjud — o\'tkazib yuborildi.'})
                continue

            try:
                Customer.objects.create(
                    store=store,
                    name=ism,
                    phone=row.get('telefon', '').strip(),
                    address=row.get('manzil', '').strip(),
                    note=row.get('izoh', '').strip(),
                    group=group,
                )
                created += 1
            except Exception as e:
                errors.append({'row': row_num, 'error': str(e)})

        return Response({'created': created, 'skipped': skipped, 'errors': errors})


# ============================================================
# IMPORT VIEWS — StockMovement (Kirim/Chiqim)
# ============================================================

MOVEMENT_HEADERS = [
    'mahsulot', 'miqdor', 'harakat_turi',
    'joy_nomi', 'joy_turi', 'tannarx', 'yetkazib_beruvchi', 'izoh',
]
MOVEMENT_NOTES = {
    'mahsulot':          'Mahsulot nomi (majburiy)',
    'miqdor':            'Miqdori — raqam (majburiy)',
    'harakat_turi':      'in (kirim) yoki out (chiqim)',
    'joy_nomi':          'Filial yoki ombor nomi (majburiy)',
    'joy_turi':          'branch (filial) yoki warehouse (ombor)',
    'tannarx':           'Birlik tannarxi (faqat kirimda, ixtiyoriy)',
    'yetkazib_beruvchi': 'Yetkazib beruvchi nomi (ixtiyoriy)',
    'izoh':              'Izoh (ixtiyoriy)',
}


class StockMovementImportView(APIView):
    permission_classes = [IsManagerOrAbove, SubscriptionRequired('has_export')]

    def get(self, request):
        return make_template('harakatlar_shablon.xlsx', MOVEMENT_HEADERS, MOVEMENT_NOTES)

    def post(self, request):
        file = request.FILES.get('file')
        if not file:
            return Response({'detail': 'file maydoni kerak.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            rows = parse_excel_upload(file)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        worker = request.user.worker
        store  = worker.store

        products   = {p.name.lower(): p for p in Product.objects.filter(store=store, status='active')}
        branches   = {b.name.lower(): b for b in Branch.objects.filter(store=store, status='active')}
        warehouses = {w.name.lower(): w for w in Warehouse.objects.filter(store=store, status='active')}
        suppliers  = {s.name.lower(): s for s in Supplier.objects.filter(store=store, status='active')}

        created = 0
        errors  = []

        for row_num, row in enumerate(rows, start=2):
            mahsulot_nom = row.get('mahsulot', '').strip().lower()
            miqdor_str   = row.get('miqdor', '').strip()
            harakat      = row.get('harakat_turi', '').strip().lower()
            joy_nom      = row.get('joy_nomi', '').strip().lower()
            joy_turi     = row.get('joy_turi', '').strip().lower()

            # Validatsiya
            product = products.get(mahsulot_nom)
            if not product:
                errors.append({'row': row_num, 'error': f'Mahsulot topilmadi: "{row.get("mahsulot")}"'})
                continue

            miqdor = _to_decimal(miqdor_str)
            if miqdor is None or miqdor <= 0:
                errors.append({'row': row_num, 'error': f'Noto\'g\'ri miqdor: "{miqdor_str}"'})
                continue

            if harakat not in ('in', 'out'):
                errors.append({'row': row_num, 'error': f'harakat_turi "in" yoki "out" bo\'lishi kerak, "{harakat}" emas.'})
                continue

            branch    = None
            warehouse = None
            if joy_turi == 'branch':
                branch = branches.get(joy_nom)
                if not branch:
                    errors.append({'row': row_num, 'error': f'Filial topilmadi: "{row.get("joy_nomi")}"'})
                    continue
            elif joy_turi == 'warehouse':
                warehouse = warehouses.get(joy_nom)
                if not warehouse:
                    errors.append({'row': row_num, 'error': f'Ombor topilmadi: "{row.get("joy_nomi")}"'})
                    continue
            else:
                errors.append({'row': row_num, 'error': 'joy_turi "branch" yoki "warehouse" bo\'lishi kerak.'})
                continue

            tannarx_str   = row.get('tannarx', '').strip()
            unit_cost     = _to_decimal(tannarx_str) if tannarx_str else None
            sup_nom       = row.get('yetkazib_beruvchi', '').strip().lower()
            supplier      = suppliers.get(sup_nom) if sup_nom else None

            try:
                with transaction.atomic():
                    mv = StockMovement.objects.create(
                        product=product,
                        branch=branch,
                        warehouse=warehouse,
                        movement_type=harakat,
                        quantity=miqdor,
                        unit_cost=unit_cost,
                        worker=worker,
                        supplier=supplier,
                        note=row.get('izoh', '').strip(),
                    )
                    # Stock qoldig'ini yangilash
                    stock, _ = Stock.objects.get_or_create(
                        product=product,
                        branch=branch,
                        warehouse=warehouse,
                        defaults={'quantity': 0},
                    )
                    if harakat == MovementType.IN:
                        stock.quantity += miqdor
                    else:
                        stock.quantity -= miqdor
                    stock.save(update_fields=['quantity'])

                    # Supplier qarz balansini yangilash (faqat IN da)
                    if harakat == MovementType.IN and supplier and unit_cost:
                        supplier.debt_balance += miqdor * unit_cost
                        supplier.save(update_fields=['debt_balance'])

                created += 1
            except Exception as e:
                errors.append({'row': row_num, 'error': str(e)})

        return Response({'created': created, 'errors': errors})


# ============================================================
# IMPORT VIEWS — Yetkazib beruvchi
# ============================================================

SUPPLIER_HEADERS = ['nom', 'kompaniya', 'telefon', 'manzil', 'izoh']
SUPPLIER_NOTES = {
    'nom':       'Yetkazib beruvchi nomi (majburiy)',
    'kompaniya': 'Kompaniya nomi (ixtiyoriy)',
    'telefon':   'Telefon (ixtiyoriy)',
    'manzil':    'Manzil (ixtiyoriy)',
    'izoh':      'Izoh (ixtiyoriy)',
}


class SupplierImportView(APIView):
    permission_classes = [IsManagerOrAbove, SubscriptionRequired('has_export')]

    def get(self, request):
        return make_template('yetkazibberuvchilar_shablon.xlsx', SUPPLIER_HEADERS, SUPPLIER_NOTES)

    def post(self, request):
        file = request.FILES.get('file')
        if not file:
            return Response({'detail': 'file maydoni kerak.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            rows = parse_excel_upload(file)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        worker = request.user.worker
        store  = worker.store

        created = 0
        skipped = 0
        errors  = []

        for row_num, row in enumerate(rows, start=2):
            nom = row.get('nom', '').strip()
            if not nom:
                errors.append({'row': row_num, 'error': 'nom maydoni bo\'sh.'})
                continue

            if Supplier.objects.filter(store=store, name=nom).exists():
                skipped += 1
                errors.append({'row': row_num, 'error': f'"{nom}" allaqachon mavjud — o\'tkazib yuborildi.'})
                continue

            try:
                Supplier.objects.create(
                    store=store,
                    name=nom,
                    company=row.get('kompaniya', '').strip(),
                    phone=row.get('telefon', '').strip(),
                    address=row.get('manzil', '').strip(),
                    note=row.get('izoh', '').strip(),
                )
                created += 1
            except Exception as e:
                errors.append({'row': row_num, 'error': str(e)})

        return Response({'created': created, 'skipped': skipped, 'errors': errors})


# ============================================================
# IMPORT VIEWS — SubKategoriya
# ============================================================

SUBCAT_HEADERS = ['nom', 'kategoriya']
SUBCAT_NOTES = {
    'nom':        'Subkategoriya nomi (majburiy)',
    'kategoriya': 'Mavjud kategoriya nomi (majburiy)',
}


class SubCategoryImportView(APIView):
    permission_classes = [IsManagerOrAbove, SubscriptionRequired('has_export')]

    def get(self, request):
        return make_template('subkategoriyalar_shablon.xlsx', SUBCAT_HEADERS, SUBCAT_NOTES)

    def post(self, request):
        file = request.FILES.get('file')
        if not file:
            return Response({'detail': 'file maydoni kerak.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            rows = parse_excel_upload(file)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        worker = request.user.worker
        store  = worker.store

        cats = {c.name.lower(): c for c in Category.objects.filter(store=store)}

        created = 0
        skipped = 0
        errors  = []

        for row_num, row in enumerate(rows, start=2):
            nom      = row.get('nom', '').strip()
            cat_nom  = row.get('kategoriya', '').strip().lower()

            if not nom:
                errors.append({'row': row_num, 'error': 'nom maydoni bo\'sh.'})
                continue

            category = cats.get(cat_nom)
            if not category:
                errors.append({'row': row_num, 'error': f'Kategoriya topilmadi: "{row.get("kategoriya")}"'})
                continue

            if SubCategory.objects.filter(category=category, name=nom).exists():
                skipped += 1
                errors.append({'row': row_num, 'error': f'"{nom}" ({category.name}) allaqachon mavjud.'})
                continue

            try:
                SubCategory.objects.create(category=category, name=nom)
                created += 1
            except Exception as e:
                errors.append({'row': row_num, 'error': str(e)})

        return Response({'created': created, 'skipped': skipped, 'errors': errors})
