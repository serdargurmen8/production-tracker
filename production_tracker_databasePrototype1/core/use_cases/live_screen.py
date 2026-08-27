"""
core/use_cases/live_screen.py
--------------------------------
Herkesin (yönetici + tabletler) gördüğü "Canlı Ekran" sekmesi.
Durum güncellemeleri on_change callback ile hatasız ve akıcı çalışır.
"""

import html as html_lib
import textwrap
from datetime import datetime

import pandas as pd
import streamlit as st
from streamlit_autorefresh import st_autorefresh

from infra.config import REFRESH_MS
from core.domain.types import STATUS_STAGES, STATUS_COLORS
from core.domain.rules import apply_insertions, compute_status, normalize_order_id
from core.repositories.status_repository import load_statuses, set_order_stage
from core.repositories.cancelled_repository import load_cancelled_orders
from core.services.pdf_service import generate_pdf
from core.use_cases.html_builder import (
    _order_table_style,
    build_order_header_html,
    build_order_row_html,
)
from ui.auth import can


# =============================================================
# GÜVENLİ CALLBACK FONKSİYONU
# =============================================================
def _handle_stage_toggle(order_id: str, stage_idx: int, current_done: int, widget_key: str):
    """
    Kullanıcı kutuyu tıkladığında Streamlit döngüsü başında çalışır.
    Durumu anında veritabanına/JSON'a kaydeder.
    """
    is_checked = st.session_state.get(widget_key, False)

    if is_checked and stage_idx == current_done:
        set_order_stage(order_id, current_done + 1)
    elif not is_checked and stage_idx == current_done - 1:
        set_order_stage(order_id, current_done - 1)


def render_status_row(row: dict, row_key: str, can_edit: bool = True) -> None:
    order_id = str(row.get("Sales Order", ""))
    done = int(row.get("_TamamlananAsama", 0) or 0)

    cols = st.columns(len(STATUS_STAGES))

    for i, stage_name in enumerate(STATUS_STAGES):
        with cols[i]:
            checked_now = i < done
            is_boundary = (i == done or i == done - 1)

            # Satıra ve tamamlanan aşamaya bağlı benzersiz widget anahtarı
            widget_key = f"chk_row_{row_key}_{i}_{done}"

            st.checkbox(
                stage_name,
                value=checked_now,
                key=widget_key,
                disabled=(not is_boundary) or (not can_edit),
                on_change=_handle_stage_toggle,
                args=(order_id, i, done, widget_key),
            )


def render_status_legend() -> None:
    swatches_html = "".join(
        f'<div style="display:flex; align-items:center; margin:6px 0;">'
        f'<span style="display:inline-block; width:20px; height:20px;'
        f'background:{STATUS_COLORS[i]}; border:1px solid rgba(0,0,0,0.25);'
        f'border-radius:4px; margin-right:10px; flex-shrink:0;"></span>'
        f'<span style="font-size:15px; font-weight:500; color:#333;">'
        f'{i + 1}. {html_lib.escape(stage_name)}</span>'
        f'</div>'
        for i, stage_name in enumerate(STATUS_STAGES)
    )

    raw = f"""
    <div style="position:fixed; top:70px; right:25px; z-index:9999;
        background:#ffffff; border:1px solid #cccccc;
        border-radius:10px; padding:14px 18px; min-width:180px;
        box-shadow:0 3px 12px rgba(0,0,0,0.18); line-height:1.3;">
        <div style="font-size:16px; font-weight:bold;
            color:#111; margin-bottom:8px; border-bottom:1px solid #eee; padding-bottom:4px;">
            🎨 Durum Renkleri
        </div>
        {swatches_html}
    </div>
    """
    st.markdown(textwrap.dedent(raw).strip(), unsafe_allow_html=True)


def render_live_screen(main_df, insertions, mtime):
    st_autorefresh(interval=REFRESH_MS, key="screen_refresh")

    render_status_legend()

    st.markdown("## Açık Siparişler - Canlı Takip")

    full_df = apply_insertions(main_df, insertions)
    full_df["_Durum"] = compute_status(full_df)

    statuses = load_statuses()
    full_df["_TamamlananAsama"] = [
        int(statuses.get(normalize_order_id(str(so)), 0))
        for so in full_df["Sales Order"]
    ]

    # ---------------------------------------------------------
    # ARAMA
    # ---------------------------------------------------------
    search = st.text_input(
        "🔍 Ara (Sales Order / Sort Name / Item Number / Açıklama)",
        placeholder="Aramak için yazın...",
        key="tv_search_input"
    )

    filtered_df = full_df
    if search:
        search_cols = ["Sales Order", "Sort Name", "Item Number", "Item Description", "Remarks"]
        mask = pd.Series(False, index=full_df.index)
        for col in search_cols:
            mask |= full_df[col].astype(str).str.contains(search, case=False, na=False, regex=False)
        filtered_df = full_df[mask]

    # =========================================================
    # PDF İNDİRME ALANI
    # =========================================================
    with st.expander("📄 PDF İndirme ve Başlık Seçenekleri", expanded=True):
        col_type, col_date = st.columns(2)
        
        with col_type:
            prod_type = st.selectbox(
                "PDF Başlık Tipi",
                options=["silindirik varil üretim", "konik varil üretim", "bidon üretim"]
            )
            
        with col_date:
            selected_date = st.date_input(
                "Üretim Tarihi",
                value=(datetime.today(), datetime.today())
            )
            if isinstance(selected_date, (list, tuple)) and len(selected_date) == 2:
                start_d, end_d = selected_date
                date_str = f"{start_d.strftime('%d.%m.')} - {end_d.strftime('%d.%m.')}"
            elif isinstance(selected_date, (list, tuple)) and len(selected_date) == 1:
                date_str = f"{selected_date[0].strftime('%d.%m.')} - {selected_date[0].strftime('%d.%m.')}"
            else:
                date_str = f"{selected_date.strftime('%d.%m.')} - {selected_date.strftime('%d.%m.')}"

        pdf_df = filtered_df.copy()
        pdf_df.insert(0, "Sıra No", range(1, len(pdf_df) + 1))

        qty_series = (
            pdf_df["Quantity Ordered"]
            .astype(str)
            .str.replace(".", "", regex=False)
            .str.replace(",", ".", regex=False)
        )
        total_quantity = int(pd.to_numeric(qty_series, errors="coerce").fillna(0).sum())

        pdf_bytes = generate_pdf(
            pdf_df, 
            prod_type=prod_type, 
            date_str=date_str, 
            total_qty=total_quantity
        )
        
        st.download_button(
            label="📄 Sipariş Listesini PDF Olarak İndir",
            data=pdf_bytes,
            file_name=f"Siparis_Listesi_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
            mime="application/pdf",
            type="primary"
        )

    st.markdown("<div style='height:15px'></div>", unsafe_allow_html=True)

    # ---------------------------------------------------------
    # TABLO RENDER
    # ---------------------------------------------------------
    display_df = filtered_df.copy()
    display_df.insert(0, "Sıra No", range(1, len(display_df) + 1))

    st.markdown(_order_table_style(), unsafe_allow_html=True)
    st.markdown(build_order_header_html(), unsafe_allow_html=True)

    if display_df.empty:
        st.info("Gösterilecek sipariş yok.")
    else:
        cancelled_set = set(load_cancelled_orders())
        records = display_df.to_dict("records")
        can_change_status = can("change_status")

        for idx, row in enumerate(records):
            row_key = f"{idx}"
            so_norm = normalize_order_id(str(row.get("Sales Order", "")))
            is_cancelled = so_norm in cancelled_set
            row_html = build_order_row_html(row)

            if is_cancelled:
                row_html = f"""
                <div style="position: relative; margin-bottom: 8px;">
                    <div style="background-color: #fff5f5; border: 1px solid #fca5a5; border-radius: 6px; padding: 2px;">
                        {row_html}
                    </div>
                    <div style="position: absolute; top: 50%; left: 0; width: 100%; transform: translateY(-50%); display: flex; align-items: center; justify-content: center; pointer-events: none; z-index: 10;">
                        <div style="flex-grow: 1; height: 4px; background-color: #dc2626; opacity: 0.9;"></div>
                        <span style="background-color: #dc2626; color: #ffffff; padding: 4px 22px; font-weight: 900; font-size: 18px; letter-spacing: 3px; border-radius: 16px; margin: 0 12px; white-space: nowrap; box-shadow: 0 3px 6px rgba(0,0,0,0.3);">
                            İPTAL
                        </span>
                        <div style="flex-grow: 1; height: 4px; background-color: #dc2626; opacity: 0.9;"></div>
                    </div>
                </div>
                """

            st.markdown(row_html, unsafe_allow_html=True)
            render_status_row(row, row_key, can_edit=can_change_status)
            st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    # ---------------------------------------------------------
    # ALT BİLGİ ÖZETİ
    # ---------------------------------------------------------
    gecikti = int((full_df["_Durum"] == "Gecikti").sum())
    bugun = int((full_df["_Durum"] == "Bugün").sum())
    acil = int(full_df["Acil"].sum())
    sevk_edildi = int((full_df["_TamamlananAsama"] >= len(STATUS_STAGES)).sum())

    son_guncelleme = mtime.strftime('%d.%m.%Y %H:%M:%S') if mtime is not None else "-"

    st.caption(
        f"🔄 {REFRESH_MS // 1000} saniyede bir otomatik yenilenir · "
        f"Son veri güncellemesi: {son_guncelleme} · "
        f"🔴 {acil} acil sipariş · "
        f"🟠 {gecikti} gecikmiş · "
        f"🟡 {bugun} bugün teslim · "
        f"🟢 {sevk_edildi} sevk edildi"
    )