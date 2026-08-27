"""
core/repositories/status_repository.py
----------------------------------------
Sipariş aşama durumlarının SQLite üzerinden yönetimi ve loglanması.
"""

from infra.db import db_session
from infra.audit import write_audit_log


def get_all_statuses() -> dict[str, int]:
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT sales_order, stage FROM order_statuses;")
        return {str(row["sales_order"]): int(row["stage"]) for row in cursor.fetchall()}


load_statuses = get_all_statuses
get_order_statuses = get_all_statuses


def set_order_stage(sales_order: str, stage: int, performed_by: str = "") -> bool:
    so = str(sales_order).strip()
    old_stage = 0
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT stage FROM order_statuses WHERE sales_order = ?;", (so,))
        row = cursor.fetchone()
        if row:
            old_stage = row["stage"]

        cursor.execute(
            """
            INSERT INTO order_statuses (sales_order, stage, updated_at)
            VALUES (?, ?, datetime('now', 'localtime'))
            ON CONFLICT(sales_order) DO UPDATE SET
                stage = excluded.stage,
                updated_at = excluded.updated_at;
            """,
            (so, int(stage))
        )

    if old_stage != stage:
        try:
            write_audit_log(
                entity_type="order_status",
                entity_id=so,
                action="stage_update",
                old_value=str(old_stage),
                new_value=str(stage),
                detail={"sales_order": so, "stage": stage},
                performed_by=performed_by or "Operatör"
            )
        except Exception:
            pass
    return True


update_order_stage = set_order_stage
save_order_stage = set_order_stage
