"""
core/repositories/cancelled_repository.py
---------------------------------------------
İptal edilen siparişlerin yönetimi.
"""

import streamlit as st

from infra.config import CANCELLED_FILE
from infra.storage import json_read, json_write
from infra.audit import write_audit_log
from core.domain.rules import normalize_order_id


def load_cancelled_orders() -> list:
    try:
        data = json_read(CANCELLED_FILE, default=[])
        return data if isinstance(data, list) else []
    except Exception:
        return []


def toggle_order_cancellation(order_id: str) -> None:
    norm_id = normalize_order_id(order_id)
    performed_by = (st.session_state.get("user") or {}).get("username", "")

    try:
        with json_write(CANCELLED_FILE, default=[]) as data:
            if norm_id in data:
                data.remove(norm_id)
                action = "uncancel"
                old_value, new_value = "İptal", "Aktif"
            else:
                data.append(norm_id)
                action = "cancel"
                old_value, new_value = "Aktif", "İptal"

        write_audit_log(
            entity_type="cancelled_orders",
            order_id=norm_id,
            action=action,
            old_value=old_value,
            new_value=new_value,
            performed_by=performed_by,
        )

    except Exception as e:
        st.error(f"❌ İptal durumu güncellenemedi: {e}")