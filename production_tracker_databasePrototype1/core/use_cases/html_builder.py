"""
core/use_cases/html_builder.py
---------------------------------
Canlı ekrandaki "iş emri kartı" tablosunu ve checkbox stillerini
tek merkezden üreten optimize edilmiş yardımcı fonksiyonlar.
"""

import html as html_lib
import textwrap
from datetime import datetime

import pandas as pd

from core.domain.types import STATUS_STAGES
from core.domain.rules import _row_bg_color

_ORDER_CARD_COLUMNS = [
    ("no",        ["No"]),
    ("musteri",   ["MUSTERI", "", "TARIH", ""]),
    ("emirno",    ["EMIR NO", "SATIS", "SO/PO", ""]),
    ("mamul",     ["MAMUL KODU", "MAMUL ADI", "", ""]),
    ("sackalin",  ["SAC KALIN", "GOVDE", "UST |ALT", "ONDULE"]),
    ("kpk",       ["KPK RENGI", "UST", "ALT", ""]),
    ("govde",     ["GOVDE RENGI", "UST & ALT", "ORTA", ""]),
    ("uretim",    ["URE", "TIM", "MKT.", ""]),
    ("logo",      ["LOGO", "", "", ""]),
    ("zaman",     ["URETIM ZAMANI", "", "", ""]),
    ("notlar",    ["NOTLAR", "", "", ""]),
    ("durum",     ["DURUM", "", "", ""]),
]

_ORDER_CARD_WIDTHS = {
    "no": 40,
    "musteri": 170,
    "emirno": 110,
    "mamul": 190,
    "sackalin": 110,
    "kpk": 90,
    "govde": 110,
    "uretim": 70,
    "logo": 70,
    "zaman": 110,
    "notlar": 90,
    "durum": 150,
}


def _order_card_esc(value) -> str:
    if value is None:
        return ""
    s = str(value).strip()
    if s.lower() == "nan":
        return ""
    return html_lib.escape(s)


def _order_row_cell_lines(row: dict) -> dict:
    """
    Sözlük formatındaki satırdan hücre çizgilerini üretir.
    Due Date dönüşümünü hızlı nesne kontrolüyle yapar.
    """
    sira_no = _order_card_esc(row.get("Sıra No", ""))
    musteri = _order_card_esc(row.get("Sort Name", ""))
    satis = _order_card_esc(row.get("Sales Order", ""))
    mamul_kodu = _order_card_esc(row.get("Item Number", ""))
    mamul_adi = _order_card_esc(row.get("Item Description", ""))
    uretim_mkt = _order_card_esc(row.get("Quantity Ordered", ""))

    # TARİH: Due Date zaten datetime olduğundan doğrudan formatlanır
    tarih = ""
    due_date_raw = row.get("Due Date", None)
    if due_date_raw is not None and pd.notna(due_date_raw):
        if isinstance(due_date_raw, (datetime, pd.Timestamp)):
            tarih = due_date_raw.strftime("%d.%m.%Y")
        else:
            ts = pd.to_datetime(due_date_raw, errors="coerce")
            if pd.notna(ts):
                tarih = ts.strftime("%d.%m.%Y")

    tamamlanan = int(row.get("_TamamlananAsama", 0) or 0)
    durum_noktalari = "".join("●" if i < tamamlanan else "○" for i in range(len(STATUS_STAGES)))
    durum_metni = "Tamamlandı" if tamamlanan >= len(STATUS_STAGES) else STATUS_STAGES[tamamlanan]

    return {
        "no": [sira_no],
        "musteri": [musteri, "", tarih],
        "emirno": [satis, ""],
        "mamul": [mamul_kodu, mamul_adi],
        "sackalin": [],
        "kpk": [],
        "govde": [],
        "uretim": [uretim_mkt],
        "logo": [],
        "zaman": [],
        "notlar": [],
        "durum": [durum_noktalari, durum_metni],
    }


def _order_table_style() -> str:
    """Tüm tablo ve durum kutucukları CSS'i tek seferde basılır."""
    raw = """
    <style>
        table.siparis-tablo {
            border-collapse: collapse;
            table-layout: fixed;
            width: 100%;
            font-family: 'Courier New', Courier, monospace;
            font-size: 18px;
            margin: 0;
            font-weight: bold;
        }
        table.siparis-tablo th,
        table.siparis-tablo td {
            border: 1px solid #000000;
            padding: 5px 9px;
            text-align: left;
            vertical-align: top;
            overflow-wrap: break-word;
            color: #000000;
        }
        table.siparis-tablo thead th {
            background-color: #ffffff;
        }

        /* Checkbox Hitbox & Stil Optimizasyonu */
        div[data-testid="stCheckbox"] label {
            display: flex !important;
            align-items: center !important;
            gap: 10px !important;
            padding: 10px 14px !important;
            width: 100% !important;
            border-radius: 6px !important;
            cursor: pointer !important;
            transition: background-color 0.15s ease !important;
        }
        div[data-testid="stCheckbox"] label:hover {
            background-color: rgba(255, 255, 255, 0.08) !important;
        }
        div[data-testid="stCheckbox"] input[type="checkbox"] {
            width: 18px !important;
            height: 18px !important;
            cursor: pointer !important;
        }
        div[data-testid="stCheckbox"] label p {
            font-size: 20px !important;
            font-weight: 600 !important;
            color: #e2e8f0 !important;
            margin: 0 !important;
        }
    </style>
    """
    return textwrap.dedent(raw).strip()


def _order_colgroup_html() -> str:
    return "<colgroup>" + "".join(
        f'<col style="width:{_ORDER_CARD_WIDTHS.get(key, 100)}px">'
        for key, _ in _ORDER_CARD_COLUMNS
    ) + "</colgroup>"


def _order_cell_html(lines) -> str:
    if not lines:
        return "&nbsp;"
    return "<br>".join(line if line else "&nbsp;" for line in lines)


def build_order_header_html() -> str:
    header_cells_html = "".join(
        f"<th>{_order_cell_html(header_lines)}</th>"
        for _, header_lines in _ORDER_CARD_COLUMNS
    )
    raw = f"""
    <table class="siparis-tablo">
      {_order_colgroup_html()}
      <thead>
        <tr>{header_cells_html}</tr>
      </thead>
    </table>
    """
    return textwrap.dedent(raw).strip()


def build_order_row_html(row: dict) -> str:
    cells = _order_row_cell_lines(row)
    bg = _row_bg_color(row)

    tds_html = "".join(
        f"<td>{_order_cell_html(cells.get(key, []))}</td>"
        for key, _ in _ORDER_CARD_COLUMNS
    )

    aciklama = _order_card_esc(row.get("Remarks", ""))
    aciklama_row_html = ""
    if aciklama:
        aciklama_colspan = len(_ORDER_CARD_COLUMNS) - 1
        aciklama_row_html = f"""
        <tr style="background-color:{bg};">
          <td style="border-top:3px solid #000000;">&nbsp;</td>
          <td colspan="{aciklama_colspan}" style="white-space:normal;border-top:3px solid #000000;">AÇIKLAMA: {aciklama}</td>
        </tr>"""

    raw = f"""
    <table class="siparis-tablo">
      {_order_colgroup_html()}
      <tbody>
        <tr style="background-color:{bg};">{tds_html}</tr>{aciklama_row_html}
      </tbody>
    </table>
    """
    return textwrap.dedent(raw).strip()