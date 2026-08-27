"""
core/repositories/excel_repository.py
---------------------------------------
Ana sipariş verisiyle ilgili tüm okuma/yazma/doğrulama işlemleri.
Streamlit 1.28 @st.cache_data standartlarına uygundur.
"""

import os
import shutil
from datetime import datetime
from io import BytesIO

import pandas as pd
import streamlit as st

from infra.config import SHEET_NAME, ORDERS_FILE, EXCEL_ARCHIVE_DIR
from core.domain.types import REQUIRED_COLUMNS
from core.domain.rules import sort_orders_by_item_number


def validate_excel_file(uploaded_file) -> tuple[bool, str]:
    """
    Kullanıcının seçtiği Excel'in doğru sipariş Excel'i
    olup olmadığını sadece başlık satırını okuyarak kontrol eder.
    """
    try:
        df = pd.read_excel(
            uploaded_file,
            sheet_name=SHEET_NAME,
            nrows=0,
            engine="openpyxl"
        )

        cols = [str(c).strip() for c in df.columns]
        missing = [col for col in REQUIRED_COLUMNS if col not in cols]

        if missing:
            return False, f"Eksik sütun(lar): {', '.join(missing)}"

        return True, ""

    except Exception as e:
        return False, f"Excel okunamadı: {e}"


def import_excel_to_db(file_bytes: bytes, uploaded_by: str = "") -> int:
    from infra.audit import write_audit_log

    df = pd.read_excel(
        BytesIO(file_bytes),
        sheet_name=SHEET_NAME,
        engine="openpyxl"
    )

    df.columns = [str(c).strip() for c in df.columns]
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]

    if missing:
        raise ValueError(f"Excel'de eksik sütun(lar): {', '.join(missing)}")

    df = df[REQUIRED_COLUMNS].copy()
    df["Due Date"] = pd.to_datetime(df["Due Date"], errors="coerce")

    # Önceki dosyayı arşivle
    if os.path.exists(ORDERS_FILE):
        os.makedirs(EXCEL_ARCHIVE_DIR, exist_ok=True)
        stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        archive_path = os.path.join(
            EXCEL_ARCHIVE_DIR,
            f"gercek_siparisler_{stamp}.xlsx",
        )
        shutil.copy2(ORDERS_FILE, archive_path)

    os.makedirs(os.path.dirname(ORDERS_FILE) or ".", exist_ok=True)
    df.to_excel(ORDERS_FILE, index=False, sheet_name="Sheet1", engine="openpyxl")

    # Önbelleği temizle
    _read_current_orders_cached.clear()

    write_audit_log(
        entity_type="orders",
        entity_id=None,
        action="import",
        new_value=f"{len(df)} satır",
        detail={"row_count": len(df)},
        performed_by=uploaded_by,
    )

    return len(df)


def has_orders() -> bool:
    if not os.path.exists(ORDERS_FILE):
        return False

    try:
        df = pd.read_excel(ORDERS_FILE, sheet_name="Sheet1", nrows=1, engine="openpyxl")
        return len(df) > 0
    except Exception:
        return False


def get_last_upload_time():
    """
    Dosyanın son değiştirilme zamanını yerel saat olarak döner.
    """
    if not os.path.exists(ORDERS_FILE):
        return None

    # utcfromtimestamp yerine doğrudan yerel saati alan fromtimestamp kullanılır
    return datetime.fromtimestamp(os.path.getmtime(ORDERS_FILE))


@st.cache_data(show_spinner=False)
def _read_current_orders_cached(cache_key: str) -> pd.DataFrame:
    """Streamlit 1.28 önbellek okuyucu ve otomatik Item Number sıralaması."""
    df = pd.read_excel(ORDERS_FILE, sheet_name="Sheet1", engine="openpyxl")
    df = df[REQUIRED_COLUMNS].copy()
    df["Due Date"] = pd.to_datetime(df["Due Date"], errors="coerce")

    # Siparişleri mamul koduna göre sırala
    df = sort_orders_by_item_number(df)

    return df


def read_main_excel() -> pd.DataFrame:
    try:
        last_upload = get_last_upload_time()
        if last_upload is None:
            st.error("❌ Henüz sipariş bulunamadı.")
            st.stop()

        cache_key = f"{last_upload.isoformat()}::{os.path.getsize(ORDERS_FILE)}"
        return _read_current_orders_cached(cache_key)

    except Exception as e:
        st.error(f"❌ Sipariş dosyası okunamadı: {e}")
        st.stop()