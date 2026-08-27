"""
infra/db.py
-------------
SQLite veritabanı bağlantısı, tablo oluşturma ve
mevcut JSON verilerini otomatik aktarma (migration) modülü.
WAL modu ile çoklu tablet/eşzamanlı yazma koruması sağlar.
"""

import json
import os
import sqlite3
from contextlib import contextmanager

# DATA_DIR infra.config'den alınır; bulunamazsa varsayılan 'data' kullanılır
try:
    from infra.config import DATA_DIR
except Exception:
    DATA_DIR = "data"

DB_FILE = os.path.join(DATA_DIR, "production.db")


def get_db_connection() -> sqlite3.Connection:
    """SQLite bağlantısı üretir ve WAL modunu aktif eder."""
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_FILE, timeout=10.0)
    conn.row_factory = sqlite3.Row  # Sözlük gibi sütun ismiyle erişim
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    return conn


@contextmanager
def db_session():
    """Otomatik commit ve rollback yapan güvenli context manager."""
    conn = get_db_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_database() -> None:
    """Tabloları oluşturur ve mevcut JSON verilerini SQLite'a aktarır."""
    with db_session() as conn:
        cursor = conn.cursor()

        # 1. Kullanıcılar Tablosu
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL,
                full_name TEXT DEFAULT '',
                created_at TEXT DEFAULT ''
            );
        """)

        # 2. Sipariş Aşamaları Tablosu
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS order_statuses (
                sales_order TEXT PRIMARY KEY,
                stage INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT DEFAULT ''
            );
        """)

        # 3. Araya Eklenen Acil Siparişler Tablosu
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS insertions (
                id TEXT PRIMARY KEY,
                target_order TEXT NOT NULL,
                position TEXT NOT NULL DEFAULT 'before',
                row_data TEXT NOT NULL,
                created_by TEXT DEFAULT '',
                created_at TEXT DEFAULT ''
            );
        """)

        # 4. İptal Edilen Siparişler Tablosu
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cancelled_orders (
                sales_order TEXT PRIMARY KEY,
                cancelled_at TEXT DEFAULT '',
                cancelled_by TEXT DEFAULT ''
            );
        """)

        # 5. Denetim Kayıtları (Audit Log) Tablosu
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_id TEXT,
                action TEXT NOT NULL,
                old_value TEXT,
                new_value TEXT,
                detail TEXT,
                performed_by TEXT
            );
        """)

    # Mevcut JSON dosyalarını kontrol et ve varsa aktar
    _migrate_existing_json_data()


def _migrate_existing_json_data() -> None:
    """Mevcut JSON dosyalarındaki verileri SQLite'a taşır."""
    with db_session() as conn:
        cursor = conn.cursor()

        # 1. Users migration
        cursor.execute("SELECT COUNT(*) FROM users;")
        users_file = os.path.join(DATA_DIR, "users.json")
        if cursor.fetchone()[0] == 0 and os.path.exists(users_file):
            try:
                with open(users_file, "r", encoding="utf-8") as f:
                    users_data = json.load(f)
                for u in users_data:
                    cursor.execute(
                        """INSERT OR IGNORE INTO users (username, password_hash, role, full_name, created_at)
                           VALUES (?, ?, ?, ?, ?)""",
                        (
                            u.get("username"),
                            u.get("password_hash"),
                            u.get("role"),
                            u.get("full_name", ""),
                            u.get("created_at", "")
                        )
                    )
            except Exception:
                pass

        # 2. Order Statuses migration (order_statuses.json veya statuses.json)
        cursor.execute("SELECT COUNT(*) FROM order_statuses;")
        if cursor.fetchone()[0] == 0:
            for s_name in ["order_statuses.json", "statuses.json"]:
                s_path = os.path.join(DATA_DIR, s_name)
                if os.path.exists(s_path):
                    try:
                        with open(s_path, "r", encoding="utf-8") as f:
                            status_data = json.load(f)
                        for so, stage in status_data.items():
                            cursor.execute(
                                "INSERT OR IGNORE INTO order_statuses (sales_order, stage) VALUES (?, ?)",
                                (str(so), int(stage))
                            )
                        break
                    except Exception:
                        pass

        # 3. Insertions migration
        cursor.execute("SELECT COUNT(*) FROM insertions;")
        ins_file = os.path.join(DATA_DIR, "insertions.json")
        if cursor.fetchone()[0] == 0 and os.path.exists(ins_file):
            try:
                with open(ins_file, "r", encoding="utf-8") as f:
                    ins_data = json.load(f)
                for ins in ins_data:
                    cursor.execute(
                        """INSERT OR IGNORE INTO insertions (id, target_order, position, row_data, created_by, created_at)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (
                            ins.get("id"),
                            ins.get("target_order"),
                            ins.get("position", "before"),
                            json.dumps(ins.get("row", {}), ensure_ascii=False),
                            ins.get("created_by", ""),
                            ins.get("created_at", "")
                        )
                    )
            except Exception:
                pass

        # 4. Cancelled Orders migration
        cursor.execute("SELECT COUNT(*) FROM cancelled_orders;")
        cancelled_file = os.path.join(DATA_DIR, "cancelled_orders.json")
        if cursor.fetchone()[0] == 0 and os.path.exists(cancelled_file):
            try:
                with open(cancelled_file, "r", encoding="utf-8") as f:
                    cancelled_data = json.load(f)
                for so in cancelled_data:
                    cursor.execute(
                        "INSERT OR IGNORE INTO cancelled_orders (sales_order) VALUES (?, ?)",
                        (str(so), "")
                    )
            except Exception:
                pass

        # 5. Audit Logs migration
        cursor.execute("SELECT COUNT(*) FROM audit_logs;")
        audit_file = os.path.join(DATA_DIR, "audit_log.json")
        if cursor.fetchone()[0] == 0 and os.path.exists(audit_file):
            try:
                with open(audit_file, "r", encoding="utf-8") as f:
                    logs = json.load(f)
                for log in logs:
                    cursor.execute(
                        """INSERT INTO audit_logs (timestamp, entity_type, entity_id, action, old_value, new_value, detail, performed_by)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            log.get("timestamp", ""),
                            log.get("entity_type", ""),
                            str(log.get("entity_id", "")) if log.get("entity_id") else None,
                            log.get("action", ""),
                            log.get("old_value", ""),
                            log.get("new_value", ""),
                            json.dumps(log.get("detail", {}), ensure_ascii=False) if log.get("detail") else None,
                            log.get("performed_by", "")
                        )
                    )
            except Exception:
                pass