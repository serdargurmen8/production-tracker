"""
core/repositories/insertions_repository.py
--------------------------------------------
Araya eklenen acil siparişlerin SQLite yönetimi ve denetim kaydı.
"""

import json
import uuid
from datetime import datetime
from infra.db import db_session
from infra.audit import write_audit_log


def load_insertions() -> list[dict]:
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, target_order, position, row_data, created_by, created_at FROM insertions;")
        rows = cursor.fetchall()
        res = []
        for r in rows:
            try:
                row_dict = json.loads(r["row_data"])
            except Exception:
                row_dict = {}
            res.append({
                "id": r["id"],
                "target_order": r["target_order"],
                "position": r["position"],
                "row": row_dict,
                "created_by": r["created_by"],
                "created_at": r["created_at"]
            })
        return res


get_all_insertions = load_insertions
get_insertions = load_insertions


def append_insertion(*args, **kwargs) -> bool:
    """
    Acil sipariş ekleme fonksiyonu (planning_screen ile tam uyumlu).
    """
    target_order = ""
    position = "before"
    row = {}
    created_by = ""
    insertion_id = str(uuid.uuid4())[:8]

    if len(args) == 1 and isinstance(args[0], dict):
        d = args[0]
        insertion_id = str(d.get("id", insertion_id))
        target_order = str(d.get("target_order", ""))
        position = str(d.get("position", "before"))
        row = d.get("row", {})
        created_by = str(d.get("created_by", ""))
    elif len(args) >= 3:
        if isinstance(args[2], dict):
            target_order = str(args[0])
            position = str(args[1])
            row = args[2]
            if len(args) >= 4:
                created_by = str(args[3])
        elif len(args) >= 4 and isinstance(args[3], dict):
            insertion_id = str(args[0])
            target_order = str(args[1])
            position = str(args[2])
            row = args[3]
            if len(args) >= 5:
                created_by = str(args[4])
    elif len(args) == 2:
        target_order = str(args[0])
        if isinstance(args[1], dict):
            row = args[1]
        else:
            position = str(args[1])

    if "target_order" in kwargs:
        target_order = str(kwargs["target_order"])
    if "position" in kwargs:
        position = str(kwargs["position"])
    if "row" in kwargs:
        row = kwargs["row"]
    if "row_data" in kwargs:
        row = kwargs["row_data"]
    if "created_by" in kwargs:
        created_by = str(kwargs["created_by"])
    if "id" in kwargs:
        insertion_id = str(kwargs["id"])
    if "insertion_id" in kwargs:
        insertion_id = str(kwargs["insertion_id"])

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row_json = json.dumps(row, ensure_ascii=False) if isinstance(row, dict) else str(row)

    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO insertions (id, target_order, position, row_data, created_by, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                target_order = excluded.target_order,
                position = excluded.position,
                row_data = excluded.row_data,
                created_by = excluded.created_by,
                created_at = excluded.created_at;
            """,
            (str(insertion_id), str(target_order), str(position), row_json, str(created_by), now_str)
        )

    try:
        write_audit_log(
            entity_type="insertion",
            entity_id=str(insertion_id),
            action="add_insertion",
            old_value="",
            new_value=str(target_order),
            detail={"target_order": target_order, "position": position, "row": row},
            performed_by=created_by or "Planlama"
        )
    except Exception:
        pass
    return True


add_insertion = append_insertion
save_insertion = append_insertion


def delete_insertion(insertion_id: str, performed_by: str = "", **kwargs) -> bool:
    iid = str(insertion_id).strip()
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM insertions WHERE id = ?;", (iid,))
        success = cursor.rowcount > 0

    if success:
        try:
            write_audit_log(
                entity_type="insertion",
                entity_id=iid,
                action="delete_insertion",
                old_value=iid,
                new_value="",
                detail={"deleted_id": iid},
                performed_by=performed_by or "Planlama"
            )
        except Exception:
            pass
    return success


remove_insertion = delete_insertion
delete_insertion_by_id = delete_insertion
