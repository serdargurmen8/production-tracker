"""
core/repositories/cancelled_repository.py
-------------------------------------------
İptal edilen siparişlerin SQLite yönetimi ve denetim kaydı.
"""

from datetime import datetime
from infra.db import db_session
from infra.audit import write_audit_log


def load_cancelled_orders() -> set[str]:
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT sales_order FROM cancelled_orders;")
        return {str(row["sales_order"]) for row in cursor.fetchall()}


def is_order_cancelled(sales_order: str) -> bool:
    so = str(sales_order).strip()
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM cancelled_orders WHERE sales_order = ?;", (so,))
        return cursor.fetchone() is not None


def toggle_order_cancellation(sales_order: str, cancelled_by: str = "", performed_by: str = "", **kwargs) -> bool:
    """Siparişin iptal durumunu tersine çevirir (İptalse açar, aktifse iptal eder)."""
    so = str(sales_order).strip()
    by_user = cancelled_by or performed_by or "Planlama"
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM cancelled_orders WHERE sales_order = ?;", (so,))
        is_cancelled = cursor.fetchone() is not None

        if is_cancelled:
            cursor.execute("DELETE FROM cancelled_orders WHERE sales_order = ?;", (so,))
            action = "restore_order"
            old_val, new_val = "cancelled", "active"
        else:
            cursor.execute(
                "INSERT INTO cancelled_orders (sales_order, cancelled_at, cancelled_by) VALUES (?, ?, ?);",
                (so, now_str, by_user)
            )
            action = "cancel_order"
            old_val, new_val = "active", "cancelled"

    try:
        write_audit_log(
            entity_type="cancelled_order",
            entity_id=so,
            action=action,
            old_value=old_val,
            new_value=new_val,
            detail={"sales_order": so},
            performed_by=by_user
        )
    except Exception:
        pass

    return not is_cancelled


# Takma adlar
get_cancelled_orders = load_cancelled_orders
cancel_order = toggle_order_cancellation
uncancel_order = toggle_order_cancellation
