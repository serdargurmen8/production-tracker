"""
ui/auth.py
------------
Kullanıcı kimlik doğrulama, oturum (session state) yönetimi
ve rol bazlı yetkilendirme modülü.
"""

import hashlib
import streamlit as st
from core.repositories.user_repository import (
    authenticate,
    create_user,
    has_any_user,
    find_user_by_username
)

ROLE_PERMISSIONS = {
    "yonetici": ["all", "excel_upload", "upload_excel", "urgent_order", "cancel_order", "user_management", "view_audit_log", "audit_log", "stage_update"],
    "admin": ["all", "excel_upload", "upload_excel", "urgent_order", "cancel_order", "user_management", "view_audit_log", "audit_log", "stage_update"],
    "planlama": ["urgent_order", "cancel_order", "stage_update", "view_audit_log", "audit_log", "excel_upload", "upload_excel"],
    "operator": ["stage_update"],
    "izleyici": [],
}


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def init_auth_session_state() -> None:
    if "authenticated_user" not in st.session_state:
        st.session_state["authenticated_user"] = None
    if "username" not in st.session_state:
        st.session_state["username"] = None
    if "role" not in st.session_state:
        st.session_state["role"] = None


def get_current_user() -> dict | None:
    return st.session_state.get("authenticated_user")


def is_authenticated() -> bool:
    return st.session_state.get("authenticated_user") is not None


def current_username() -> str:
    u = get_current_user()
    return u.get("username", "Anonim") if u else "Anonim"


def can(permission: str) -> bool:
    user = get_current_user()
    if not user:
        return False
    role = str(user.get("role", "")).lower()
    perms = ROLE_PERMISSIONS.get(role, [])
    return "all" in perms or permission in perms


def login_user(username: str, password: str) -> tuple[bool, str]:
    if not username.strip() or not password.strip():
        return False, "Kullanıcı adı ve şifre boş bırakılamaz."

    pwd_hash = hash_password(password.strip())
    user = authenticate(username.strip(), password_hash=pwd_hash, password=password.strip())

    if user:
        st.session_state["authenticated_user"] = user
        st.session_state["username"] = user.get("username")
        st.session_state["role"] = user.get("role")
        return True, "Giriş başarılı."

    return False, "Kullanıcı adı veya şifre hatalı, ya da hesap pasif."


def logout() -> None:
    for k in ["authenticated_user", "username", "role", "selected_tab", "main_active_tab"]:
        if k in st.session_state:
            del st.session_state[k]


def render_login() -> None:
    with st.sidebar:
        if is_authenticated():
            u = get_current_user()
            st.markdown(f"👤 **{u.get('username')}** `({u.get('role')})`")
            if st.button("🚪 Çıkış Yap", use_container_width=True):
                logout()
                st.rerun()
        else:
            st.markdown("### 🔑 Giriş Yap")
            with st.form("sidebar_login_form"):
                u = st.text_input("Kullanıcı Adı")
                p = st.text_input("Şifre", type="password")
                sub = st.form_submit_button("Giriş", type="primary", use_container_width=True)
                if sub:
                    ok, msg = login_user(u, p)
                    if ok:
                        st.rerun()
                    else:
                        st.error(msg)


def render_first_admin_setup() -> None:
    st.markdown("### 🛠️ İlk Yönetici Hesabını Oluşturun")
    st.info("Sistemde kayıtlı kullanıcı bulunamadı. Lütfen ilk yöneticiyi belirleyin.")

    with st.form("setup_admin_form"):
        u = st.text_input("Yönetici Kullanıcı Adı")
        fn = st.text_input("Ad Soyad")
        p = st.text_input("Şifre", type="password")
        p2 = st.text_input("Şifre Tekrar", type="password")
        sub = st.form_submit_button("Yöneticiyi Oluştur ve Başla", type="primary")

        if sub:
            if not u.strip() or not p.strip():
                st.error("Kullanıcı adı ve şifre zorunludur.")
            elif p != p2:
                st.error("Şifreler birbiriyle eşleşmiyor.")
            else:
                ok, msg = create_user(
                    username=u.strip(),
                    password_hash=hash_password(p.strip()),
                    role="yonetici",
                    full_name=fn.strip(),
                    created_by="Sistem"
                )
                if ok:
                    st.success("✅ Yönetici oluşturuldu! Soldaki menüden giriş yapabilirsiniz.")
                    st.rerun()
                else:
                    st.error(msg)
