"""
ui/user_management.py
------------------------
Sadece ADMIN rolündeki kullanıcıların gördüğü "Kullanıcı Yönetimi"
sekmesi: kullanıcı oluşturma, rol değiştirme, aktif/pasif etme ve
şifre sıfırlama.
"""

import streamlit as st

from core.domain.permissions import ROLES, ROLE_LABELS
from core.repositories.user_repository import (
    list_users,
    create_user,
    set_user_role,
    set_user_active,
    reset_password,
)
from ui.auth import current_username


def render_user_management_tab() -> None:

    st.markdown("### 👥 Kullanıcı Yönetimi")

    st.caption(
        "Burada oluşturduğunuz kullanıcılar, giriş ekranındaki "
        "kullanıcı adı/şifre ile sisteme girer. Her rolün neye "
        "izin verdiği: İzleyici → sadece canlı ekran · "
        "Operatör → + durum değiştirme · "
        "Planlamacı → + acil sipariş/iptal · "
        "Yönetici → + Excel yükleme ve kullanıcı yönetimi."
    )

    # ---------------------------------------------------------
    # YENİ KULLANICI OLUŞTUR
    # ---------------------------------------------------------
    with st.expander("➕ Yeni kullanıcı oluştur", expanded=False):

        with st.form("create_user_form", clear_on_submit=True):

            col1, col2 = st.columns(2)

            with col1:
                new_username = st.text_input("Kullanıcı adı")
                new_role = st.selectbox(
                    "Rol",
                    ROLES,
                    format_func=lambda r: f"{ROLE_LABELS.get(r, r)} ({r})",
                )

            with col2:
                new_pw1 = st.text_input("Şifre", type="password")
                new_pw2 = st.text_input("Şifre (tekrar)", type="password")

            submitted = st.form_submit_button("Kullanıcı oluştur", type="primary")

            if submitted:

                if new_pw1 != new_pw2:
                    st.error("❌ Şifreler eşleşmiyor.")

                else:

                    ok, msg = create_user(
                        username=new_username,
                        password=new_pw1,
                        role=new_role,
                        created_by=current_username(),
                    )

                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

    st.divider()

    # ---------------------------------------------------------
    # MEVCUT KULLANICILAR
    # ---------------------------------------------------------
    st.markdown("#### Mevcut kullanıcılar")

    users = list_users()

    if not users:
        st.info("Henüz kullanıcı yok.")
        return

    for u in users:

        with st.container():

            c1, c2, c3, c4 = st.columns([3, 2, 2, 3])

            with c1:
                status = "🟢" if u["active"] else "⚪"
                st.write(f"{status} **{u['username']}**")
                if u["last_login_at"]:
                    st.caption(f"Son giriş: {u['last_login_at']}")
                else:
                    st.caption("Hiç giriş yapmadı")

            with c2:

                role_index = ROLES.index(u["role"]) if u["role"] in ROLES else 0

                selected_role = st.selectbox(
                    "Rol",
                    ROLES,
                    index=role_index,
                    key=f"role_select_{u['id']}",
                    format_func=lambda r: ROLE_LABELS.get(r, r),
                    label_visibility="collapsed",
                )

                if selected_role != u["role"]:

                    if st.button(
                        "Rolü kaydet",
                        key=f"role_save_{u['id']}",
                        use_container_width=True,
                    ):

                        ok, msg = set_user_role(
                            u["id"], selected_role, performed_by=current_username()
                        )

                        (st.success if ok else st.error)(msg)

                        if ok:
                            st.rerun()

            with c3:

                is_self = u["username"] == current_username()

                toggle_label = "🔴 Pasif et" if u["active"] else "🟢 Aktif et"

                if st.button(
                    toggle_label,
                    key=f"toggle_active_{u['id']}",
                    use_container_width=True,
                    disabled=is_self,
                    help="Kendi hesabınızı pasif edemezsiniz." if is_self else None,
                ):

                    ok, msg = set_user_active(
                        u["id"], not u["active"], performed_by=current_username()
                    )

                    (st.success if ok else st.error)(msg)

                    if ok:
                        st.rerun()

            with c4:

                with st.expander("🔑 Şifre sıfırla"):

                    with st.form(f"reset_pw_form_{u['id']}", clear_on_submit=True):

                        new_pw = st.text_input(
                            "Yeni şifre", type="password", key=f"new_pw_{u['id']}"
                        )

                        reset_submitted = st.form_submit_button("Sıfırla")

                        if reset_submitted:

                            ok, msg = reset_password(
                                u["id"], new_pw, performed_by=current_username()
                            )

                            (st.success if ok else st.error)(msg)
