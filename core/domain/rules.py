"""
core/domain/rules.py
----------------------
Saf iş kuralları: girdi alır, çıktı döndürür; dosya/DB/Streamlit
ile hiç konuşmaz.
"""

import re
import pandas as pd
from core.domain.types import STATUS_COLORS


def normalize_order_id(value) -> str:
    s = str(value).strip()
    if s.endswith(".0"):
        head = s[:-2]
        if head.isdigit():
            return head
    return s


def extract_color_suffix(item_number) -> str:
    """
    Mamul kodunun sonundaki, rakamlardan sonra gelen renk kodunu ayıklar.
    Örnekler:
      'TR12216111CML'   -> 'CML'
      'TR39218676MKAS'  -> 'MKAS'
      'TR123'           -> ''
    """
    if item_number is None or pd.isna(item_number):
        return ""

    s = str(item_number).strip().upper()
    if s.endswith(".0") and s[:-2].isdigit():
        s = s[:-2]

    match = re.search(r"\d([A-Z].*)$", s)
    if match:
        return match.group(1).strip()

    return ""


def sort_orders_by_item_number(df: pd.DataFrame) -> pd.DataFrame:
    """
    3 Aşamalı Sıralama Algoritması:
      1. ADIM: Tüm listeyi 'Item Number'a göre alfabetik sıralar (sayılar harflerden önce).
      2. ADIM: Alfabetik sıradaki ilk karşılaşılan renge göre, aynı renk koduna sahip
               diğer tüm ürünleri onun hemen arkasına çekerek yer değişimi yapar.
      3. ADIM: Gruplanmış blokları birleştirerek listeyi nihai forma getirir.
    """
    if "Item Number" not in df.columns or df.empty:
        return df

    def _clean_sort_key(val):
        if pd.isna(val) or val is None:
            return ""
        s = str(val).strip()
        if s.endswith(".0") and s[:-2].isdigit():
            s = s[:-2]
        return s.upper()

    # ---------------------------------------------------------
    # 1. ADIM: Saf Alfabetik Sıralama
    # ---------------------------------------------------------
    df_step1 = df.copy()
    df_step1["_sort_key"] = df_step1["Item Number"].apply(_clean_sort_key)
    df_step1 = (
        df_step1.sort_values(by="_sort_key", ascending=True, kind="stable")
        .drop(columns=["_sort_key"])
    )

    # ---------------------------------------------------------
    # 2. ADIM: Aynı Renkleri İlk Görüldükleri Yerde Bir Araya Getirme
    # ---------------------------------------------------------
    df_step1["_color_suffix"] = df_step1["Item Number"].apply(extract_color_suffix)

    color_order = []
    color_groups = {}

    for record in df_step1.to_dict("records"):
        color = record["_color_suffix"]
        if color not in color_groups:
            color_order.append(color)
            color_groups[color] = []
        color_groups[color].append(record)

    # ---------------------------------------------------------
    # 3. ADIM: Nihai Formu Oluşturma
    # ---------------------------------------------------------
    final_records = []
    for color in color_order:
        final_records.extend(color_groups[color])

    df_final = pd.DataFrame(final_records)
    if "_color_suffix" in df_final.columns:
        df_final = df_final.drop(columns=["_color_suffix"])

    return df_final.reset_index(drop=True)


def apply_insertions(df: pd.DataFrame, insertions: list) -> pd.DataFrame:
    df = df.reset_index(drop=True).copy()
    df["Acil"] = False

    if not insertions:
        return df

    records = df.to_dict("records")

    for insertion in insertions:
        if not isinstance(insertion, dict):
            continue

        target = normalize_order_id(insertion.get("target_order", ""))
        position = insertion.get("position", "before")
        row = dict(insertion.get("row", {}))
        row["Acil"] = True

        matches = [
            i for i, record in enumerate(records)
            if normalize_order_id(record.get("Sales Order", "")) == target
        ]

        if matches:
            index = matches[0] if position == "before" else matches[-1] + 1
        else:
            index = len(records)

        records.insert(index, row)

    return pd.DataFrame(records)


def compute_status(df: pd.DataFrame) -> pd.Series:
    today = pd.Timestamp.today().normalize()
    due_dates = pd.to_datetime(df["Due Date"], errors="coerce").dt.normalize()

    status = pd.Series("Planlandı", index=df.index)
    status[due_dates.isna()] = "Belirsiz"
    status[due_dates < today] = "Gecikti"
    status[due_dates == today] = "Bugün"

    return status


def _row_bg_color(row: dict) -> str:
    if row.get("Acil", False):
        return "#ffcccc"

    tamamlanan = int(row.get("_TamamlananAsama", 0) or 0)
    if tamamlanan > 0:
        idx = min(tamamlanan, len(STATUS_COLORS)) - 1
        return STATUS_COLORS[idx]

    durum = row.get("_Durum", "")
    if durum == "Gecikti":
        return "#ffe1b3"
    if durum == "Bugün":
        return "#fff3cd"
    if durum == "Belirsiz":
        return "#f1f1f1"

    return "#ffffff"