"""
infra/audit.py
----------------
Tüm audit_log.json yazımlarının tek geçtiği yer.
ID hesaplaması tip güvenli hale getirilmiş ve log temizleme fonksiyonu eklenmiştir.
"""

from datetime import datetime

from infra.config import AUDIT_LOG_FILE
from infra.request_context import get_client_ip
from infra.storage import json_write

_next_id_cache = None


def _safe_int_id(val) -> int:
    """UUID veya bozuk ID değerleri gelse bile hata vermeden 0 kabul eder."""
    try:
        return int(val)
    except (ValueError, TypeError):
        return 0


def write_audit_log(
    *,
    entity_type: str,
    action: str,
    performed_by: str = "",
    entity_id: str = None,
    order_id: str = None,
    old_value=None,
    new_value=None,
    detail: dict = None,
) -> None:
    """
    order_id: mümkün olduğunda doldurulmalı.
    old_value / new_value: kısa, insana okunur metin.
    """
    try:
        with json_write(AUDIT_LOG_FILE, default=[]) as logs:
            max_id = max((_safe_int_id(row.get("id", 0)) for row in logs), default=0)
            new_id = max_id + 1

            logs.append(
                {
                    "id": new_id,
                    "entity_type": str(entity_type or ""),
                    "entity_id": str(entity_id) if entity_id is not None else None,
                    "order_id": str(order_id) if order_id is not None else None,
                    "action": str(action or ""),
                    "old_value": _stringify(old_value),
                    "new_value": _stringify(new_value),
                    "detail": detail,
                    "performed_by": str(performed_by or ""),
                    "performed_at": datetime.utcnow().isoformat(),
                    "ip_address": get_client_ip(),
                }
            )
    except Exception:
        pass


def clear_audit_logs(performed_by: str = "") -> bool:
    """Tüm denetim loglarını sıfırlar ve temizleme kaydını 1 ID'si ile yazar."""
    try:
        with json_write(AUDIT_LOG_FILE, default=[]) as logs:
            logs.clear()
            logs.append(
                {
                    "id": 1,
                    "entity_type": "audit_log",
                    "entity_id": None,
                    "order_id": None,
                    "action": "clear",
                    "old_value": None,
                    "new_value": None,
                    "detail": {"message": "Tüm önceki test ve işlem kayıtları temizlendi."},
                    "performed_by": str(performed_by or "admin"),
                    "performed_at": datetime.utcnow().isoformat(),
                    "ip_address": get_client_ip(),
                }
            )
        return True
    except Exception:
        return False


def _stringify(value):
    if value is None:
        return None
    return str(value)