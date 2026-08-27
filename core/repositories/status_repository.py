"""
core/repositories/status_repository.py
---------------------------------------------
Sipariş aşama durumlarının (Dikiş -> Sevk) yönetimi.
"""

import streamlit as st

from infra.config import STATUS_FILE
from infra.storage import json_read, json_write
from infra.audit import write_audit_log
from core.domain.types import STATUS_STAGES
from core.domain.rules import normalize_order_id


def _stage_label(stage: int) -> str:
    if not stage:
        return "Başlamadı"
    index = max(0, min(len(STATUS_STAGES), stage)) - 1
    return STATUS_STAGES[index]


def load_statuses() -> dict:
    try:
        data = json_read(STATUS_FILE, default={})
        return {k: int(v) for k, v in data.items()} if isinstance(data, dict) else {}
    except Exception as e:
        st.warning(f"⚠️ Durum bilgisi okunamadı: {e}")
        return {}


def set_order_stage(order_id: str, new_stage: int) -> bool:
    normalized = normalize_order_id(order_id)
    new_stage = max(0, min(len(STATUS_STAGES), new_stage))
    updated_by = (st.session_state.get("user") or {}).get("username", "")

    try:
        with json_write(STATUS_FILE, default={}) as data:
            old_stage = int(data.get(normalized, 0))
            if new_stage == 0:
                data.pop(normalized, None)
            else:
                data[normalized] = new_stage

        if old_stage != new_stage:
            write_audit_log(
                entity_type="production_status",
                order_id=normalized,
                action="status_change",
                old_value=_stage_label(old_stage),
                new_value=_stage_label(new_stage),
                performed_by=updated_by,
            )
        return True
    except Exception as e:
        st.error(f"❌ Durum kaydedilemedi: {e}")
        return False