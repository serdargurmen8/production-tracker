"""
ui/audit_log.py
------------------
Denetim kayıtlarını listeleyen ve yöneticilere geçmişi
temizleme imkanı sunan ekran (SQLite uyumlu).
"""

import pandas as pd
import streamlit as st

from ui.auth import can
from core.repositories.audit_repository import list_audit_logs, clear_audit_logs


def render_audit_log_tab() -> None:
    st.markdown("### 🧾 Denetim Kaydı (Audit Log)")
    st.caption(
        "Sistemde yapılan durum değişiklikleri, acil sipariş ekleme/silme ve kullanıcı işlemleri burada listelenir."
    )

    # ---------------------------------------------------------
    # KAYITLARI TEMİZLEME ALANI (SADECE YÖNETİCİ)
    # ---------------------------------------------------------
    if can("user_management"):
        with st.expander("🗑️ Geçmiş Logları Temizle", expanded=False):
            st.warning("⚠️ Bu işlem tüm geçmiş denetim kayıtlarını kalıcı olarak siler.")

            if st.button("Tüm Kayıtları Kalıcı Olarak Temizle", type="primary"):
                if clear_audit_logs():
                    st.success("✅ Tüm kayıtlar başarıyla temizlendi.")
                else:
                    st.error("❌ Kayıtlar temizlenirken bir hata oluştu.")

    st.divider()

    # ---------------------------------------------------------
    # LOGLARI LİSTELEME
    # ---------------------------------------------------------
    logs = list_audit_logs()

    if not logs:
        st.info("Kayıtlı işlem geçmişi bulunmuyor.")
        return

    df_logs = pd.DataFrame(logs)

    # id sütununu görselde gizleyelim
    if "id" in df_logs.columns:
        df_logs = df_logs.drop(columns=["id"])

    st.dataframe(
        df_logs,
        use_container_width=True,
        hide_index=True
    )