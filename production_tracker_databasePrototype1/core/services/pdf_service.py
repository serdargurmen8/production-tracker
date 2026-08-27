"""
core/services/pdf_service.py
-------------------------------
Filtrelenmiş sipariş tablosunu, iş emri formatında yüksek hızlı
ReportLab motoruyla PDF'e dönüştüren servis.
"""

import os
from io import BytesIO
from datetime import datetime, timedelta
import pandas as pd

from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Font Tanımlamaları
font_path = "C:/Windows/Fonts/arial.ttf"
font_bold_path = "C:/Windows/Fonts/arialbd.ttf"

if os.path.exists(font_path) and os.path.exists(font_bold_path):
    pdfmetrics.registerFont(TTFont('ArialCustom', font_path))
    pdfmetrics.registerFont(TTFont('ArialCustom-Bold', font_bold_path))
    FONT_NAME = 'ArialCustom'
    FONT_BOLD_NAME = 'ArialCustom-Bold'
else:
    FONT_NAME = 'Helvetica'
    FONT_BOLD_NAME = 'Helvetica-Bold'


def clean_text(val) -> str:
    if val is None or pd.isna(val):
        return ""
    s = str(val).strip()
    return "" if s.lower() == "nan" else s


PRODUCTION_START_HOUR = 7
PRODUCTION_START_MINUTE = 30
UNITS_PER_HOUR = 406


def _parse_quantity(val) -> float:
    if val is None or pd.isna(val):
        return 0.0
    try:
        return float(val)
    except (TypeError, ValueError):
        try:
            cleaned = str(val).strip().replace(".", "").replace(",", ".")
            return float(cleaned)
        except (TypeError, ValueError):
            return 0.0


def _format_time(dt: datetime) -> str:
    if dt.minute == 0:
        return f"{dt.hour}"
    return f"{dt.hour}:{dt.minute:02d}"


def generate_pdf(df: pd.DataFrame, prod_type: str = "silindirik varil üretim", date_str: str = "", total_qty: int = 0) -> BytesIO:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=landscape(A4), 
        rightMargin=15, 
        leftMargin=15, 
        topMargin=15, 
        bottomMargin=15
    )
    elements = []
    
    styles = getSampleStyleSheet()
    normal_style = styles['Normal']
    normal_style.fontName = FONT_NAME
    normal_style.fontSize = 8
    normal_style.leading = 10
    
    header_style = ParagraphStyle(
        'HeaderStyle',
        parent=normal_style,
        fontName=FONT_BOLD_NAME,
        fontSize=8,
        leading=10
    )

    box_style = ParagraphStyle(
        'AsciiBoxStyle',
        fontName='Courier-Bold',
        fontSize=10,
        leading=12,
        alignment=1
    )

    inner_text = f" {prod_type}    {date_str}    (Toplam)   Toplami: {total_qty} "
    dash_border = "+" + "-" * (len(inner_text) - 2) + "+"
    middle_line = f"|{inner_text[1:-1]}|".replace(" ", "&nbsp;")
    ascii_box_html = f"{dash_border}<br/>{middle_line}<br/>{dash_border}"

    elements.append(Paragraph(ascii_box_html, box_style))
    elements.append(Spacer(1, 10))

    headers = [
        "No", "MÜŞTERİ\nTARİH / AÇIKLAMA", "EMİR NO\nSATIŞ", 
        "MAMÜL KODU\nMAMÜL ADI", "SAC KALIN\nGÖVDE | ÜST/ALT", 
        "KPK RENGİ\nÜST / ALT", "GÖVDE RENGİ\nORTA", 
        "ÜRETİM\nMKT.", "LOGO", "ÜR. ZAMANI", "NOTLAR"
    ]
    
    table_data = [[Paragraph(h.replace('\n', '<br/>'), header_style) for h in headers]]
    num_cols = len(headers)
    extra_style_commands = []
    row_index = 1

    current_time = datetime(2000, 1, 1, PRODUCTION_START_HOUR, PRODUCTION_START_MINUTE)

    # iterrows yerine hızlı sözlük iterasyonu
    records = df.to_dict("records")

    for idx, row in enumerate(records):
        sira = clean_text(row.get("Sıra No", idx + 1))
        musteri = clean_text(row.get("Sort Name", ""))
        aciklama = clean_text(row.get("Remarks", ""))
        
        tarih = ""
        due_date_raw = row.get("Due Date")
        if due_date_raw is not None and pd.notna(due_date_raw):
            if isinstance(due_date_raw, (datetime, pd.Timestamp)):
                tarih = due_date_raw.strftime("%d.%m.%Y")
            else:
                try:
                    tarih = pd.to_datetime(due_date_raw).strftime("%d.%m.%Y")
                except Exception:
                    tarih = clean_text(due_date_raw)
            
        col_musteri_parts = [p for p in [musteri, tarih] if p]
        col_musteri = "<br/>".join(col_musteri_parts)
        
        satis = clean_text(row.get("Sales Order", ""))
        mamul_kodu = clean_text(row.get("Item Number", ""))
        mamul_adi = clean_text(row.get("Item Description", ""))
        col_mamul = f"<b>{mamul_kodu}</b><br/>{mamul_adi}" if mamul_kodu or mamul_adi else ""
        
        qty_raw = row.get("Quantity Ordered", "")
        mkt = clean_text(qty_raw)
        
        qty = _parse_quantity(qty_raw)
        if qty > 0:
            duration_minutes = (60.0 * qty) / UNITS_PER_HOUR
            end_time = current_time + timedelta(minutes=duration_minutes)
            ur_zamani = f"{_format_time(current_time)} - {_format_time(end_time)}"
            current_time = end_time
        else:
            ur_zamani = ""
        
        row_cells = [
            Paragraph(sira, normal_style),
            Paragraph(col_musteri, normal_style),
            Paragraph(satis, normal_style),
            Paragraph(col_mamul, normal_style),
            Paragraph("", normal_style),
            Paragraph("", normal_style),
            Paragraph("", normal_style),
            Paragraph(mkt, normal_style),
            Paragraph("", normal_style),
            Paragraph(ur_zamani, normal_style),
            Paragraph("", normal_style)
        ]
        table_data.append(row_cells)
        row_index += 1

        if aciklama:
            aciklama_cells = [Paragraph("", normal_style) for _ in range(num_cols)]
            aciklama_cells[1] = Paragraph(f"<b>AÇIKLAMA:</b> {aciklama}", normal_style)
            table_data.append(aciklama_cells)

            extra_style_commands.append(('SPAN', (1, row_index), (num_cols - 1, row_index)))
            extra_style_commands.append(('LINEBELOW', (1, row_index), (num_cols - 1, row_index), 1.2, colors.black))
            row_index += 1
        
    col_widths = [30, 150, 80, 160, 80, 60, 70, 50, 45, 60, 60]
    t = Table(table_data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
    ] + extra_style_commands))
    
    elements.append(t)
    doc.build(elements)
    buffer.seek(0)
    return buffer