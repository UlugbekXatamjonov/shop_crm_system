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
