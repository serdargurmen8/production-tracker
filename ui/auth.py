"""
ui/auth.py
------------
Kişi bazlı giriş/çıkış ve ilk kurulumda ilk ADMIN hesabının
oluşturulması.

Eskiden (MASTER_PASSWORD) herkes aynı şifreyi paylaşıyordu ve
"siparişi kim değiştirdi?" sorusunun cevabı yoktu. Artık her
kullanıcının kendi kullanıcı adı/şifresi ve rolü (core/domain/
permissions.py) var; session_state.user bu bilgiyi tutar ve
diğer tüm modüller kimin işlem yaptığını buradan öğrenir.
"""

from typing import Optional

import streamlit as st

from infra.config import SETUP_KEY
from core.domain.permissions import ROLES, ROLE_LABELS, can as role_can
from core.repositories.user_repository import authenticate, create_user, has_any_user


# =============================================================
# SESSION STATE YARDIMCILARI
# =============================================================
def init_auth_session_state() -> None:

    if "user" not in st.session_state:
        st.session_state.user = None


def current_user() -> Optional[dict]:
    return st.session_state.get("user")


def is_authenticated() -> bool:
    return current_user() is not None


def current_username() -> str:
    user = current_user()
    return user["username"] if user else ""


def current_role() -> str:
    user = current_user()
    return user["role"] if user else ""


def can(action: str) -> bool:
    """Giriş yapmış kullanıcının belirtilen işlemi yapıp yapamayacağı."""

    user = current_user()

    if not user:
        return False

    return role_can(user["role"], action)


# =============================================================
# İLK KURULUM: HİÇ KULLANICI YOKSA İLK ADMIN HESABINI OLUŞTUR
# =============================================================
def render_first_admin_setup() -> None:

    st.markdown(
        """
        <div style="text-align:center; padding:40px 20px 20px 20px;">
            <h1>📦 Sipariş Takip Sistemi</h1>
            <p style="font-size:18px;">İlk kurulum: yönetici hesabı oluşturun</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.info(
        "Sistemde henüz hiçbir kullanıcı yok. Devam etmek için "
        "bir yönetici (ADMIN) hesabı oluşturun. Bu ekran sadece "
        "veritabanında hiç kullanıcı yokken görünür."
    )

    with st.form("first_admin_setup_form", clear_on_submit=False):

        setup_key = st.text_input(
            "Kurulum anahtarı (SETUP_KEY)",
            type="password",
            help="Sunucuyu kuran kişiden alınan tek seferlik anahtar.",
        )

        username = st.text_input("Yönetici kullanıcı adı")

        pw1 = st.text_input("Şifre", type="password")
        pw2 = st.text_input("Şifre (tekrar)", type="password")

        submitted = st.form_submit_button("Yönetici hesabını oluştur", type="primary")

        if submitted:

            if setup_key != SETUP_KEY:
                st.error("❌ Kurulum anahtarı hatalı.")

            elif not username.strip():
                st.error("❌ Kullanıcı adı boş olamaz.")

            elif pw1 != pw2:
                st.error("❌ Şifreler eşleşmiyor.")

            else:

                ok, msg = create_user(
                    username=username,
                    password=pw1,
                    role="ADMIN",
                    created_by="setup",
                )

                if ok:
                    st.success(msg + " Şimdi giriş yapabilirsiniz.")
                    st.rerun()
                else:
                    st.error(msg)

    st.stop()


# =============================================================
# GİRİŞ / ÇIKIŞ
# =============================================================
def render_login() -> None:
    """
    Sidebar'da kullanıcı adı/şifre girişi gösterir. Giriş başarılı
    olursa session_state.user rolüyle birlikte doldurulur.
    """

    with st.sidebar:

        st.markdown("### 🔑 Giriş")

        user = current_user()

        if user:

            role_label = ROLE_LABELS.get(user["role"], user["role"])

            st.success(f"**{user['username']}** ({role_label})")

            if st.button("Çıkış yap", use_container_width=True):
                st.session_state.user = None
                st.rerun()

        else:

            with st.form("login_form", clear_on_submit=False):

                username = st.text_input("Kullanıcı adı")
                password = st.text_input("Şifre", type="password")

                submitted = st.form_submit_button("Giriş yap", use_container_width=True)

                if submitted:

                    logged_in_user = authenticate(username, password)

                    if logged_in_user:
                        st.session_state.user = logged_in_user
                        st.rerun()
                    else:
                        st.error("❌ Kullanıcı adı veya şifre hatalı, ya da hesap pasif.")

            st.caption("Giriş yapmadan sisteme erişilemez.")
