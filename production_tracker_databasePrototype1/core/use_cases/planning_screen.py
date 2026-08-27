"""
core/use_cases/planning_screen.py
------------------------------------
"Araya Acil Sipariş Ekle/Çıkar" ve "Sipariş İptal / Aktif Durumu" sekmesi.
Çift tetiklenme sorunu giderilmiştir.
"""

from datetime import date
import streamlit as st

from core.domain.rules import apply_insertions, normalize_order_id
from core.repositories.insertions_repository import (
    load_insertions,
    append_insertion,
    remove_insertion,
)
from core.repositories.cancelled_repository import (
    load_cancelled_orders,
    toggle_order_cancellation,
)
from ui.auth import current_username, can


def render_planning_tab(main_df, insertions):
    # En güncel acil sipariş listesini dinamik al
    current_insertions = load_insertions()

    if not can("urgent_order"):
        st.info("Bu bölüm için yetkiniz yok.")
    else:
        _render_urgent_order_section(main_df, current_insertions)

    st.divider()

    if not can("cancel_order"):
        st.info("Sipariş iptal etme yetkiniz yok.")
    else:
        _render_cancel_section(main_df, current_insertions)


def _render_urgent_order_section(main_df, insertions):
    st.markdown("### ⚡ Araya Acil Sipariş Ekle/Çıkar")
    st.caption(
        "Bu formla eklediğiniz sipariş ana Excel dosyanızı "
        "değiştirmez. Canlı ekranda seçtiğiniz siparişin "
        "önüne veya arkasına kırmızı vurgulu olarak yerleşir."
    )

    full_current_df = apply_insertions(main_df, insertions)

    order_list = (
        full_current_df["Sales Order"]
        .astype(str)
        .unique()
        .tolist()
    )

    excel_order_ids = {
        normalize_order_id(value)
        for value in main_df["Sales Order"]
    }

    with st.form("araya_ekleme_formu", clear_on_submit=True):
        col1, col2 = st.columns(2)

        with col1:
            target_order = st.selectbox("📌 Hangi Sales Order referans alınsın?", order_list)
            position_choice = st.radio("Konum:", ["Seçilenin Önüne", "Seçilenin Arkasına"], horizontal=True)
            new_sales_order = st.text_input("Yeni Sales Order", value="ACIL-001")
            new_sort_name = st.text_input("Sort Name", value="")

        with col2:
            new_item_number = st.text_input("Item Number", value="")
            new_item_desc = st.text_input("Item Description", value="")
            new_qty = st.number_input("Quantity Ordered", min_value=1, value=1)
            new_due = st.date_input("Due Date", value=date.today())
            new_remarks = st.text_input("Remarks", value="ACİL - Araya Alındı")

        submitted = st.form_submit_button("Araya Ekle", type="primary")

        if submitted:
            clean_so = new_sales_order.strip()
            if not clean_so:
                st.error("❌ Sales Order boş olamaz.")
            else:
                new_row = {
                    "Sales Order": clean_so,
                    "Sort Name": new_sort_name,
                    "Item Number": new_item_number,
                    "Item Description": new_item_desc,
                    "Quantity Ordered": new_qty,
                    "Due Date": new_due.strftime("%Y-%m-%d"),
                    "Remarks": new_remarks,
                }

                ok, msg = append_insertion(
                    target_order=target_order,
                    position="before" if "Önüne" in position_choice else "after",
                    row=new_row,
                    excel_order_ids=excel_order_ids,
                    created_by=current_username(),
                )

                if ok:
                    st.success(msg)
                    # Listeyi anında güncelle
                    insertions = load_insertions()
                else:
                    st.error(msg)

    st.divider()
    st.markdown("#### Şu an araya eklenmiş siparişler")

    if not insertions:
        st.info("Araya eklenmiş sipariş yok.")
    else:
        for insertion in insertions:
            if not isinstance(insertion, dict):
                continue

            row = insertion.get("row", {})
            insertion_id = insertion.get("id", "")
            target = insertion.get("target_order", "?")
            position = insertion.get("position", "before")
            position_text = "önüne" if position == "before" else "arkasına"
            created_by = insertion.get("created_by", "")
            created_at = insertion.get("created_at", "")

            info_suffix = ""
            if created_by:
                info_suffix = f" · ekleyen: {created_by}"
                if created_at:
                    info_suffix += f" ({created_at})"

            col1, col2 = st.columns([5, 1])
            with col1:
                st.write(
                    f"**{row.get('Sales Order', '?')}** "
                    f"— {row.get('Item Description', '')} "
                    f"({position_text}: {target})"
                    f"{info_suffix}"
                )

            with col2:
                if st.button("Kaldır", key=f"btn_del_{insertion_id}"):
                    if remove_insertion(insertion_id):
                        st.rerun()


def _render_cancel_section(main_df, insertions):
    full_current_df = apply_insertions(main_df, insertions)

    st.markdown("### 🚫 Sipariş İptal / Aktif Durumu")
    st.caption("Aşağıdaki listeden siparişleri tamamen silmeden iptal edebilirsiniz. İptal edilen siparişlerin ekranda üstü çizilir.")

    cancelled_orders = set(load_cancelled_orders())
    unique_orders_df = full_current_df[["Sales Order", "Sort Name", "Item Description"]].drop_duplicates("Sales Order")
    records = unique_orders_df.to_dict("records")

    for idx, row in enumerate(records):
        so_id = str(row.get("Sales Order", ""))
        norm_id = normalize_order_id(so_id)
        is_cancelled = norm_id in cancelled_orders
        
        c1, c2 = st.columns([5, 2])
        with c1:
            label = f"**{so_id}** — {row.get('Sort Name', '')} ({row.get('Item Description', '')})"
            if is_cancelled:
                st.markdown(f"~~{label}~~ ❌ *(İptal Edildi)*")
            else:
                st.markdown(f"✅ {label}")
                
        with c2:
            btn_label = "🟢 Aktif Et" if is_cancelled else "🔴 İptal Et (Üstünü Çiz)"
            if st.button(btn_label, key=f"btn_cancel_{norm_id}_{idx}"):
                toggle_order_cancellation(so_id)
                st.rerun()