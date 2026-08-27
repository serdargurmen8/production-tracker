"""
infra/audit.py
----------------
Sistem denetim kayıtlarını SQLite audit_logs tablosuna işler.
"""

import json
from datetime import datetime
from infra.db import db_session


def write_audit_log(
    entity_type: str,
    entity_id: str | None,
    action: str,
    old_value: str = "",
    new_value: str = "",
    detail: dict | None = None,
    performed_by: str = "",
    **kwargs
) -> None:
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    detail_str = json.dumps(detail, ensure_ascii=False) if (detail and isinstance(detail, (dict, list))) else (str(detail) if detail else "")

    try:
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO audit_logs (
                    timestamp, entity_type, entity_id, action,
                    old_value, new_value, detail, performed_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    now_str,
                    str(entity_type),
                    str(entity_id) if entity_id is not None else "",
                    str(action),
                    str(old_value) if old_value is not None else "",
                    str(new_value) if new_value is not None else "",
                    detail_str,
                    str(performed_by or "Sistem")
                )
            )
    except Exception:
        pass


log_action = write_audit_log
log_event = write_audit_log
