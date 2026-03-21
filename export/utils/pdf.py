"""
============================================================
PDF HELPER — reportlab asosida
============================================================
Funksiyalar:
  make_pdf_response  — title + headers + rows → HttpResponse (.pdf)
"""

import io

from django.http import HttpResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os

# ============================================================
# SHRIFT SOZLAMALARI
# Agar DejaVu (unicode) shrift bo'lmasa — standart Helvetica
# ============================================================

_FONT_REGISTERED = False
_FONT_NAME = 'Helvetica'


def _try_register_font():
    global _FONT_REGISTERED, _FONT_NAME
    if _FONT_REGISTERED:
        return
    font_paths = [
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        '/usr/share/fonts/dejavu/DejaVuSans.ttf',
        'C:/Windows/Fonts/arial.ttf',
    ]
    for path in font_paths:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont('CustomFont', path))
                _FONT_NAME = 'CustomFont'
                break
            except Exception:
                pass
    _FONT_REGISTERED = True


# ============================================================
# RANG KONSTANTALARI
# ============================================================

COLOR_HEADER  = colors.HexColor('#2E75B6')
COLOR_ROW_ODD = colors.HexColor('#EBF3FB')
COLOR_BORDER  = colors.HexColor('#BDD7EE')
COLOR_WHITE   = colors.white
COLOR_BLACK   = colors.black


# ============================================================
# ASOSIY FUNKSIYA
# ============================================================

def make_pdf_response(
    filename: str,
    title: str,
    headers: list[str],
    rows: list[list],
    landscape_mode: bool = False,
) -> HttpResponse:
    """
    filename       — 'sales_report.pdf'
    title          — sarlavha matni
    headers        — ustun nomlari ro'yxati
    rows           — ma'lumot qatorlari ro'yxati
    landscape_mode — True bo'lsa sahifa gorizontal (keng jadvallar uchun)
    """
    _try_register_font()
    styles = getSampleStyleSheet()

    page_size = landscape(A4) if landscape_mode else A4
    buffer    = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=page_size,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )

    title_style = ParagraphStyle(
        'Title',
        fontName=_FONT_NAME,
        fontSize=14,
        textColor=COLOR_HEADER,
        spaceAfter=6,
        leading=18,
    )
    cell_style = ParagraphStyle(
        'Cell',
        fontName=_FONT_NAME,
        fontSize=8,
        leading=11,
        wordWrap='LTR',
    )

    # ---- Ustun kengligi ----
    page_width = (landscape(A4)[0] if landscape_mode else A4[0]) - 30 * mm
    col_count  = len(headers)
    col_width  = page_width / col_count

    # ---- Jadval ma'lumotlari ----
    table_data = [[
        Paragraph(f'<b>{h}</b>', ParagraphStyle(
            'H', fontName=_FONT_NAME, fontSize=9,
            textColor=COLOR_WHITE, leading=12,
        ))
        for h in headers
    ]]

    for row in rows:
        table_data.append([
            Paragraph(str(v) if v is not None else '', cell_style)
            for v in row
        ])

    # ---- Jadval stili ----
    row_count  = len(table_data)
    table_style_cmds = [
        # Header
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_HEADER),
        ('TEXTCOLOR',  (0, 0), (-1, 0), COLOR_WHITE),
        ('ALIGN',      (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN',     (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME',   (0, 0), (-1, 0), _FONT_NAME),
        ('FONTSIZE',   (0, 0), (-1, 0), 9),
        ('ROWBACKGROUND', (0, 0), (-1, 0), COLOR_HEADER),
        # Ma'lumot qatorlari — zebra stripes
        ('ROWBACKGROUND', (0, 1), (-1, -1), COLOR_WHITE),
        ('GRID',       (0, 0), (-1, -1), 0.4, COLOR_BORDER),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
    ]
    # Toq qatorlar — och ko'k
    for i in range(1, row_count):
        if i % 2 == 1:
            table_style_cmds.append(
                ('BACKGROUND', (0, i), (-1, i), COLOR_ROW_ODD)
            )

    table = Table(
        table_data,
        colWidths=[col_width] * col_count,
        repeatRows=1,
    )
    table.setStyle(TableStyle(table_style_cmds))

    elements = [
        Paragraph(title, title_style),
        Spacer(1, 4 * mm),
        table,
    ]

    doc.build(elements)
    buffer.seek(0)

    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


# ============================================================
# SOTUV CHEK PDF
# ============================================================

def make_receipt_pdf(sale, request=None) -> HttpResponse:
    """
    Sotuv cheki PDF.

    sale — trade.models.Sale instance (items prefetch_related bo'lishi kerak)
    request — optional, URL qurilishi uchun

    Chek formati: 80mm termik printer uslubida (tor sahifa)
    """
    from reportlab.lib.pagesizes import mm as mm_unit
    from reportlab.platypus import HRFlowable

    _try_register_font()
    fn = _FONT_NAME

    # 80 mm termik printer eni
    PAGE_W = 80 * mm_unit
    PAGE_H = 297 * mm_unit   # yetarlicha baland; platypus avtomatik qisqartiradi

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=(PAGE_W, PAGE_H),
        leftMargin=4 * mm,
        rightMargin=4 * mm,
        topMargin=6 * mm,
        bottomMargin=6 * mm,
    )

    styles  = getSampleStyleSheet()
    W       = PAGE_W - 8 * mm   # foydalanilgan kenglik

    # --- Yordamchi uslublar ---
    def _style(size=8, bold=False, align='LEFT', color=COLOR_BLACK):
        return ParagraphStyle(
            f'custom_{size}_{bold}_{align}',
            fontName=fn,
            fontSize=size,
            leading=size + 3,
            alignment={'LEFT': 0, 'CENTER': 1, 'RIGHT': 2}[align],
            textColor=color,
        )

    def _p(text, **kw):
        return Paragraph(text, _style(**kw))

    def _hr():
        return HRFlowable(width='100%', thickness=0.4, color=colors.grey, spaceAfter=3)

    # --- Ma'lumotlar ---
    store_name  = sale.store.name if sale.store else ''
    branch_name = sale.branch.name if sale.branch else ''
    cashier     = sale.worker.user.get_full_name() if sale.worker_id else ''
    created_on  = sale.created_on.strftime('%d.%m.%Y %H:%M') if sale.created_on else ''
    payment_map = {
        'cash':  'Naqd',
        'card':  'Karta',
        'mixed': 'Aralash',
        'debt':  'Nasiya',
    }
    payment_label = payment_map.get(sale.payment_type, sale.payment_type)

    net_total = sale.total_price - sale.discount_amount

    items_qs = sale.items.select_related('product').all()

    # --- Elementlar ---
    elements = [
        _p(store_name,  size=11, bold=True, align='CENTER', color=COLOR_HEADER),
        _p(branch_name, size=8,  align='CENTER'),
        Spacer(1, 2 * mm),
        _hr(),
        _p(f"Chek #: <b>{sale.pk}</b>", size=8),
        _p(f"Sana: {created_on}",        size=8),
        _p(f"Kassir: {cashier}",         size=8),
    ]

    if sale.customer_id:
        customer_name = sale.customer.name if sale.customer else ''
        elements.append(_p(f"Mijoz: {customer_name}", size=8))

    elements += [
        _hr(),
        # --- Mahsulotlar jadvali ---
        Table(
            [
                [
                    Paragraph('<b>Mahsulot</b>',  _style(size=7, bold=True)),
                    Paragraph('<b>Miqdor</b>',    _style(size=7, bold=True, align='RIGHT')),
                    Paragraph('<b>Narx</b>',       _style(size=7, bold=True, align='RIGHT')),
                    Paragraph('<b>Jami</b>',       _style(size=7, bold=True, align='RIGHT')),
                ]
            ] + [
                [
                    Paragraph(item.product.name[:30], _style(size=7)),
                    Paragraph(
                        f"{item.quantity:g}",
                        _style(size=7, align='RIGHT'),
                    ),
                    Paragraph(
                        f"{item.unit_price:,.0f}",
                        _style(size=7, align='RIGHT'),
                    ),
                    Paragraph(
                        f"{item.total_price:,.0f}",
                        _style(size=7, align='RIGHT'),
                    ),
                ]
                for item in items_qs
            ],
            colWidths=[W * 0.44, W * 0.14, W * 0.20, W * 0.22],
            style=TableStyle([
                ('VALIGN',       (0, 0), (-1, -1), 'TOP'),
                ('LINEBELOW',    (0, 0), (-1, 0),  0.4, colors.grey),
                ('TOPPADDING',   (0, 0), (-1, -1), 2),
                ('BOTTOMPADDING',(0, 0), (-1, -1), 2),
                ('LEFTPADDING',  (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ]),
        ),
        _hr(),
    ]

    # --- Summa bloki ---
    def _sum_row(label, value, bold=False):
        return Table(
            [[_p(label, size=8, bold=bold), _p(value, size=8, bold=bold, align='RIGHT')]],
            colWidths=[W * 0.55, W * 0.45],
            style=TableStyle([
                ('TOPPADDING',    (0, 0), (-1, -1), 1),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
                ('LEFTPADDING',   (0, 0), (-1, -1), 0),
                ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
            ]),
        )

    elements.append(_sum_row('JAMI (chegirmasiz):', f"{sale.total_price:,.0f}"))
    if sale.discount_amount:
        elements.append(_sum_row(f"Chegirma:", f"-{sale.discount_amount:,.0f}"))
    elements.append(_sum_row("TO'LOV:", f"{net_total:,.0f}", bold=True))
    elements.append(Spacer(1, 2 * mm))
    elements.append(_sum_row(f"To'lov turi:", payment_label))
    elements.append(_sum_row("To'langan:", f"{sale.paid_amount:,.0f}"))
    if sale.debt_amount:
        elements.append(_sum_row("Qarz:", f"{sale.debt_amount:,.0f}"))

    elements += [
        _hr(),
        _p("Xarid uchun rahmat!", size=9, align='CENTER'),
    ]

    doc.build(elements)
    buffer.seek(0)

    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="receipt_{sale.pk}.pdf"'
    return response
