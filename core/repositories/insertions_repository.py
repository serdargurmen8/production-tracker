"""
core/repositories/insertions_repository.py
---------------------------------------------
Araya eklenen acil siparişlerin yönetimi.
"""

import uuid
from datetime import datetime
import streamlit as st

from infra.config import INSERTIONS_FILE
from infra.storage import json_read, json_write
from infra.audit import write_audit_log
from core.domain.rules import normalize_order_id


def load_insertions() -> list:
    try:
        data = json_read(INSERTIONS_FILE, default=[])
        return data if isinstance(data, list) else []
    except Exception as e:
        st.warning(f"⚠️ Acil sipariş listesi okunamadı: {e}")
        return []


def append_insertion(
    target_order: str,
    position: str,
    row: dict,
    excel_order_ids: set,
    created_by: str = ""
) -> tuple[bool, str]:

    clean_so = str(row.get("Sales Order", "")).strip()
    normalized_so = normalize_order_id(clean_so)

    if normalized_so in excel_order_ids:
        return False, f"❌ '{clean_so}' zaten ana Excel'de mevcut."

    try:
        with json_write(INSERTIONS_FILE, default=[]) as data:
            duplicate = any(
                normalize_order_id(item.get("row", {}).get("Sales Order", "")) == normalized_so
                for item in data if isinstance(item, dict)
            )

            if duplicate:
                return False, f"❌ '{clean_so}' zaten kullanımda."

            row_with_flag = dict(row)
            row_with_flag["Acil"] = True
            new_id = str(uuid.uuid4())

            data.append({
                "id": new_id,
                "target_order": str(target_order),
                "position": position,
                "row": row_with_flag,
                "created_by": created_by,
                "created_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            })

        write_audit_log(
            entity_type="insertions",
            entity_id=new_id,
            order_id=normalized_so,
            action="create",
            new_value=f"{clean_so} ({position}: {target_order})",
            detail={"target_order": str(target_order), "position": position},
            performed_by=created_by,
        )

        return True, f"✅ {clean_so} araya eklendi."

    except Exception as e:
        return False, f"❌ Kaydetme hatası: {e}"


def remove_insertion(insertion_id: str) -> bool:
    try:
        removed_order_id = None
        removed_target = None

        with json_write(INSERTIONS_FILE, default=[]) as data:
            for item in data:
                if str(item.get("id")) == str(insertion_id):
                    removed_order_id = normalize_order_id(item.get("row", {}).get("Sales Order", ""))
                    removed_target = item.get("target_order")
                    break

            data[:] = [item for item in data if str(item.get("id")) != str(insertion_id)]

        if removed_order_id is not None:
            write_audit_log(
                entity_type="insertions",
                entity_id=str(insertion_id),
                order_id=removed_order_id,
                action="delete",
                old_value=removed_target,
                performed_by=(st.session_state.get("user") or {}).get("username", ""),
            )

        return True

    except Exception as e:
        st.error(f"❌ Silme hatası: {e}")
        return False