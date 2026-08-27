"""
core/repositories/audit_repository.py
---------------------------------------
Denetim kayıtlarının SQLite üzerinden okunması ve temizlenmesi.
"""

import json
from infra.db import db_session


def list_audit_logs() -> list[dict]:
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, timestamp, entity_type, entity_id, action,
                   old_value, new_value, detail, performed_by
            FROM audit_logs
            ORDER BY id DESC;
            """
        )
        rows = cursor.fetchall()
        logs = []
        for row in rows:
            item = dict(row)
            if item.get("detail"):
                try:
                    item["detail"] = json.loads(item["detail"])
                except Exception:
                    pass
            logs.append(item)
        return logs


get_audit_logs = list_audit_logs
load_audit_logs = list_audit_logs
read_audit_logs = list_audit_logs


def clear_audit_logs() -> bool:
    try:
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM audit_logs;")
            cursor.execute("DELETE FROM sqlite_sequence WHERE name = 'audit_logs';")
        return True
    except Exception:
        return False
