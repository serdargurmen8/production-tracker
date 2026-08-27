"""
core/repositories/audit_repository.py
---------------------------------------
Denetim kayıtlarının okunması ve sıfırlanması işlemleri.
"""

import json
import os

from infra.config import AUDIT_LOG_FILE
from infra.storage import json_read


def list_audit_logs() -> list:
    """Tüm denetim kayıtlarını döner."""
    logs = json_read(AUDIT_LOG_FILE, default=[])
    return logs if isinstance(logs, list) else []


def clear_audit_logs() -> bool:
    """
    Denetim kaydı dosyasını geride hiçbir kayıt bırakmadan
    tamamen sıfırlar (boş liste).
    """
    lock_file = AUDIT_LOG_FILE + ".lock"

    if os.path.exists(lock_file):
        try:
            os.remove(lock_file)
        except OSError:
            pass

    try:
        os.makedirs(os.path.dirname(AUDIT_LOG_FILE) or ".", exist_ok=True)

        with open(AUDIT_LOG_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)

        return True
    except Exception:
        return False