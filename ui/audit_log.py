"""
ui/audit_log.py
------------------
Denetim kayıtlarını listeleyen ve yöneticilere geçmişi
temizleme imkanı sunan ekran.
"""

import pandas as pd
import streamlit as st

from infra.config import AUDIT_LOG_FILE
from infra.storage import json_read
from ui.auth import can
from core.repositories.audit_repository import clear_audit_logs


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
    logs = json_read(AUDIT_LOG_FILE, default=[])

    if not logs:
        st.info("Kayıtlı işlem geçmişi bulunmuyor.")
        return

    df_logs = pd.DataFrame(logs)
    if not df_logs.empty and "timestamp" in df_logs.columns:
        df_logs = df_logs.iloc[::-1].reset_index(drop=True)
    elif not df_logs.empty and "performed_at" in df_logs.columns:
        df_logs = df_logs.iloc[::-1].reset_index(drop=True)

    st.dataframe(
        df_logs,
        use_container_width=True,
        hide_index=True
    )