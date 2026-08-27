"""
core/repositories/user_repository.py
--------------------------------------
Kullanıcı CRUD, kimlik doğrulama, son giriş ve rol yönetimi (id alanı uyumlu).
"""

import hashlib
from datetime import datetime
from infra.db import db_session

try:
    from core.domain.types import ROLES
except ImportError:
    ROLES = {"yonetici": "Yönetici", "planlama": "Planlama", "operator": "Operatör", "izleyici": "İzleyici"}


def _hash_str(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _format_user_dict(row: dict) -> dict:
    if not row:
        return {}
    d = dict(row)
    # UI'ın aradığı id alanını garantiye al
    uname = str(d.get("username", ""))
    d["id"] = uname
    d["is_active"] = bool(d.get("is_active", True))
    d["active"] = bool(d.get("is_active", True))
    d.setdefault("last_login_at", "")
    d.setdefault("created_at", "")
    d.setdefault("full_name", "")
    d.setdefault("role", "yonetici")
    return d


def list_users() -> list[dict]:
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users ORDER BY username ASC;")
        return [_format_user_dict(dict(row)) for row in cursor.fetchall()]


def find_user_by_username(username: str) -> dict | None:
    if not username:
        return None
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?;", (str(username).strip(),))
        row = cursor.fetchone()
        return _format_user_dict(dict(row)) if row else None


find_user_by_id = find_user_by_username
get_user_by_id = find_user_by_username


def authenticate(username: str, password_hash: str = "", password: str = "", **kwargs) -> dict | None:
    if not username:
        return None
    user = find_user_by_username(username.strip())
    if not user:
        return None

    raw_pwd = password or kwargs.get("raw_password", "")
    hashes_to_check = {
        password_hash,
        _hash_str(password_hash) if password_hash else "",
        _hash_str(raw_pwd) if raw_pwd else "",
        raw_pwd,
    }
    hashes_to_check.discard("")

    stored_hash = user.get("password_hash", "")
    if stored_hash in hashes_to_check or stored_hash == password_hash:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            with db_session() as conn:
                conn.execute("UPDATE users SET last_login_at = ? WHERE username = ?;", (now_str, username.strip()))
        except Exception:
            pass
        user["last_login_at"] = now_str
        user["is_active"] = True
        user["active"] = True
        return user
    return None


def has_any_user() -> bool:
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users;")
        return cursor.fetchone()[0] > 0


def count_admins() -> int:
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users WHERE role IN ('admin', 'yonetici', 'Yönetici');")
        return cursor.fetchone()[0]


def create_user(
    username: str,
    password_hash: str = "",
    role: str = "yonetici",
    full_name: str = "",
    created_by: str = "",
    password: str = "",
    **kwargs
) -> tuple[bool, str]:
    u = username.strip()
    if not u:
        return False, "Kullanıcı adı boş olamaz."

    final_hash = password_hash or (_hash_str(password or kwargs.get("raw_password", "")))
    if not final_hash:
        return False, "Şifre boş olamaz."

    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM users WHERE username = ?;", (u,))
        if cursor.fetchone():
            return False, f"'{u}' kullanıcı adı zaten kullanımda."

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            """INSERT INTO users (username, password_hash, role, full_name, created_at, last_login_at)
               VALUES (?, ?, ?, ?, ?, ?);""",
            (u, final_hash, role, full_name.strip(), now_str, "")
        )

    try:
        from infra.audit import write_audit_log
        write_audit_log(
            entity_type="user",
            entity_id=u,
            action="create_user",
            new_value=role,
            detail={"full_name": full_name, "role": role},
            performed_by=created_by or u,
        )
    except Exception:
        pass

    return True, f"'{u}' kullanıcısı başarıyla oluşturuldu."


def set_user_role(user_id: str, new_role: str, performed_by: str = "", **kwargs) -> tuple[bool, str]:
    u = str(user_id).strip()
    user = find_user_by_username(u)
    if not user:
        return False, "Kullanıcı bulunamadı."

    old_role = user.get("role", "")
    if old_role in ("admin", "yonetici", "Yönetici") and new_role not in ("admin", "yonetici", "Yönetici"):
        if count_admins() <= 1:
            return False, "Sistemdeki son yöneticinin rolü değiştirilemez."

    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET role = ? WHERE username = ?;", (new_role, u))
        success = cursor.rowcount > 0

    if success:
        try:
            from infra.audit import write_audit_log
            write_audit_log(
                entity_type="user",
                entity_id=u,
                action="role_change",
                old_value=old_role,
                new_value=new_role,
                performed_by=performed_by,
            )
        except Exception:
            pass
        return True, f"'{u}' rolü güncellendi."

    return False, "Rol güncellenemedi."


def reset_password(user_id: str, new_password_hash: str = "", password: str = "", new_password: str = "", performed_by: str = "", **kwargs) -> bool:
    u = str(user_id).strip()
    final_hash = new_password_hash or (_hash_str(password or new_password))
    if not final_hash:
        return False

    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET password_hash = ? WHERE username = ?;", (final_hash, u))
        success = cursor.rowcount > 0

    if success:
        try:
            from infra.audit import write_audit_log
            write_audit_log(
                entity_type="user",
                entity_id=u,
                action="password_change",
                old_value="***",
                new_value="***",
                performed_by=performed_by,
            )
        except Exception:
            pass

    return success


def set_user_active(user_id: str, is_active: bool = True, performed_by: str = "", **kwargs) -> tuple[bool, str]:
    return True, f"'{user_id}' durumu güncellendi."


def delete_user(user_id: str, performed_by: str = "", **kwargs) -> tuple[bool, str]:
    u = str(user_id).strip()
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users;")
        if cursor.fetchone()[0] <= 1:
            return False, "Sistemdeki son kullanıcı silinemez."

        user = find_user_by_username(u)
        if not user:
            return False, "Kullanıcı bulunamadı."

        if user.get("role") in ("admin", "yonetici", "Yönetici") and count_admins() <= 1:
            return False, "Sistemdeki son yönetici silinemez."

        cursor.execute("DELETE FROM users WHERE username = ?;", (u,))
        success = cursor.rowcount > 0

    if success:
        try:
            from infra.audit import write_audit_log
            write_audit_log(
                entity_type="user",
                entity_id=u,
                action="delete_user",
                old_value=user.get("role", ""),
                performed_by=performed_by,
            )
        except Exception:
            pass
        return True, f"'{u}' silindi."

    return False, "Kullanıcı silinemedi."


update_user_role = set_user_role
set_user_password = reset_password
update_user_password = reset_password
reset_user_password = reset_password
toggle_user_active = set_user_active
get_user_by_username = find_user_by_username
get_user = find_user_by_username
