"""
core/repositories/user_repository.py
---------------------------------------------
kullanicilar.json üzerinden kullanıcı yönetimi ve kimlik
doğrulama.

Bu modül MASTER_PASSWORD'ün yerini alır: artık her kullanıcının
kendi kullanıcı adı/şifresi ve rolü vardır, böylece her değişikliğin
"kim tarafından" yapıldığı sorgulanabilir (bkz. audit_log.json).
"""

from datetime import datetime

import streamlit as st

from infra.config import USERS_FILE
from infra.storage import json_read, json_write
from infra.audit import write_audit_log
from infra.security import hash_password, verify_password
from core.domain.permissions import is_valid_role


def _next_id(users: list) -> int:
    return max((u.get("id", 0) for u in users), default=0) + 1


# =============================================================
# OKUMA
# =============================================================
def has_any_user() -> bool:
    """
    Sistemde hiç kullanıcı yoksa (ilk kurulum) True döner; app.py
    bu durumda ilk yönetici hesabını oluşturma ekranını gösterir.
    """

    try:

        return len(json_read(USERS_FILE, default=[])) > 0

    except Exception:

        return False


def list_users() -> list:

    try:

        users = json_read(USERS_FILE, default=[])

        return sorted(users, key=lambda u: u.get("username", ""))

    except Exception as e:

        st.error(f"❌ Kullanıcılar okunamadı: {e}")

        return []


def get_user_by_username(username: str):

    if not username:
        return None

    try:

        users = json_read(USERS_FILE, default=[])

        for u in users:

            if u.get("username") == username.strip():
                return u

        return None

    except Exception:

        return None


# =============================================================
# KİMLİK DOĞRULAMA
# =============================================================
def authenticate(username: str, password: str):
    """
    Kullanıcı adı/şifre doğruysa ve hesap aktifse kullanıcı
    bilgisini (dict) döner; aksi halde None döner. Sebep (kullanıcı
    yok / şifre yanlış / hesap pasif) kasıtlı olarak dışa
    sızdırılmaz - hepsi aynı genel "kullanıcı adı veya şifre
    hatalı" mesajına düşer.
    """

    username = (username or "").strip()

    if not username or not password:
        return None

    try:

        with json_write(USERS_FILE, default=[]) as users:

            user = next(
                (u for u in users if u.get("username") == username),
                None,
            )

            if user is None or not user.get("active", True):
                return None

            if not verify_password(password, user.get("password_hash", "")):
                return None

            user["last_login_at"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            result = dict(user)

        write_audit_log(
            entity_type="users",
            entity_id=str(result.get("id")),
            action="login",
            performed_by=result.get("username"),
        )

        return result

    except Exception as e:

        st.error(f"❌ Giriş sırasında bir hata oluştu: {e}")

        return None


# =============================================================
# YAZMA (yalnızca ADMIN ekranından çağrılır; yetki kontrolü
# çağıran UI katmanında yapılır - core/domain/permissions.py)
# =============================================================
def create_user(
    username: str,
    password: str,
    role: str,
    created_by: str = "",
) -> tuple:
    """(ok: bool, message: str) döner."""

    username = (username or "").strip()

    if not username:
        return False, "❌ Kullanıcı adı boş olamaz."

    if not password or len(password) < 6:
        return False, "❌ Şifre en az 6 karakter olmalı."

    if not is_valid_role(role):
        return False, f"❌ Geçersiz rol: {role}"

    try:

        new_id = None

        with json_write(USERS_FILE, default=[]) as users:

            existing = next(
                (u for u in users if u.get("username") == username),
                None,
            )

            if existing is not None:
                return False, "❌ Bu kullanıcı adı zaten kullanılıyor."

            new_id = _next_id(users)

            users.append(
                {
                    "id": new_id,
                    "username": username,
                    "password_hash": hash_password(password),
                    "role": role,
                    "active": True,
                    "created_by": created_by,
                    "created_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                    "last_login_at": "",
                }
            )

        write_audit_log(
            entity_type="users",
            entity_id=str(new_id),
            action="create",
            new_value=f"{username} ({role})",
            detail={"username": username, "role": role},
            performed_by=created_by,
        )

        return True, f"✅ Kullanıcı oluşturuldu: {username} ({role})"

    except Exception as e:

        return False, f"❌ Kullanıcı oluşturulamadı: {e}"


def set_user_role(user_id: int, role: str, performed_by: str = "") -> tuple:

    if not is_valid_role(role):
        return False, f"❌ Geçersiz rol: {role}"

    try:

        old_role = None
        found = False

        with json_write(USERS_FILE, default=[]) as users:

            for u in users:

                if u.get("id") == user_id:

                    old_role = u.get("role")
                    u["role"] = role
                    found = True
                    break

            if not found:
                return False, "❌ Kullanıcı bulunamadı."

        write_audit_log(
            entity_type="users",
            entity_id=str(user_id),
            action="update_role",
            old_value=old_role,
            new_value=role,
            performed_by=performed_by,
        )

        return True, "✅ Rol güncellendi."

    except Exception as e:

        return False, f"❌ Rol güncellenemedi: {e}"


def set_user_active(user_id: int, active: bool, performed_by: str = "") -> tuple:

    try:

        old_active = None
        found = False

        with json_write(USERS_FILE, default=[]) as users:

            for u in users:

                if u.get("id") == user_id:

                    old_active = u.get("active", True)
                    u["active"] = active
                    found = True
                    break

            if not found:
                return False, "❌ Kullanıcı bulunamadı."

        write_audit_log(
            entity_type="users",
            entity_id=str(user_id),
            action="activate" if active else "deactivate",
            old_value="Aktif" if old_active else "Pasif",
            new_value="Aktif" if active else "Pasif",
            performed_by=performed_by,
        )

        return True, ("✅ Kullanıcı aktif edildi." if active else "✅ Kullanıcı pasif edildi.")

    except Exception as e:

        return False, f"❌ İşlem başarısız: {e}"


def reset_password(user_id: int, new_password: str, performed_by: str = "") -> tuple:

    if not new_password or len(new_password) < 6:
        return False, "❌ Şifre en az 6 karakter olmalı."

    try:

        found = False

        with json_write(USERS_FILE, default=[]) as users:

            for u in users:

                if u.get("id") == user_id:

                    u["password_hash"] = hash_password(new_password)
                    found = True
                    break

            if not found:
                return False, "❌ Kullanıcı bulunamadı."

        write_audit_log(
            entity_type="users",
            entity_id=str(user_id),
            action="reset_password",
            # Şifrenin kendisi asla audit kaydına yazılmaz.
            performed_by=performed_by,
        )

        return True, "✅ Şifre sıfırlandı."

    except Exception as e:

        return False, f"❌ Şifre sıfırlanamadı: {e}"
