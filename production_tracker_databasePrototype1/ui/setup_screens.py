"""
ui/setup_screens.py
----------------------
İlk kurulum (Excel seçme) ekranı ve yöneticinin günlük Excel
güncelleme paneli.
"""

import time

import streamlit as st

from core.repositories.excel_repository import validate_excel_file, import_excel_to_db
from ui.auth import current_username


# =============================================================
# YENİ: GÜNLÜK EXCEL GÜNCELLEME (SADECE YÖNETİCİ)
# =============================================================
def render_daily_excel_uploader():
    """
    Yönetici, ERP'den gelen o günkü excel'i buradan
    istediği zaman yükleyip mevcut dosyanın üzerine yazabilir.
    Eski dosya otomatik olarak arşivlenir.
    """

    with st.sidebar:

        st.divider()

        st.markdown(
            "### 📤 Bugünün excelini yükle"
        )

        st.caption(
            "Yeni excel yüklendiğinde eskisi otomatik arşivlenir."
        )

        new_file = st.file_uploader(
            "İş emri excelini seç (.xlsx)",
            type=["xlsx"],
            key="daily_excel_uploader"
        )

        if new_file is not None:

            valid, err = validate_excel_file(
                new_file
            )

            if not valid:

                st.error(
                    f"❌ Bu dosya uygun değil: {err}"
                )

            else:

                st.success(
                    "✅ Dosya uygun görünüyor."
                )

                if st.button(
                    "Excel'i güncelle",
                    type="primary",
                    use_container_width=True
                ):

                    try:

                        import_excel_to_db(
                            new_file.getvalue(),
                            uploaded_by=current_username(),
                        )

                        st.cache_data.clear()

                        st.success(
                            "✅ Excel veritabanına aktarıldı."
                        )

                        time.sleep(0.5)

                        st.rerun()

                    except Exception as e:

                        st.error(
                            f"❌ Excel güncellenemedi: {e}"
                        )


# =============================================================
# EXCEL SEÇME EKRANI (İLK KURULUM)
# =============================================================
def excel_selection_screen():

    st.markdown(
        """
        <div style="
            text-align:center;
            padding:40px 20px 20px 20px;
        ">
            <h1>📦 Sipariş Takip Sistemi</h1>
            <p style="font-size:18px;">
                Ana sipariş Excel dosyası bulunamadı.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.divider()

    st.info(
        "📂 Sistemi kullanabilmek için "
        "sipariş Excel dosyanızı seçin."
    )

    uploaded_file = st.file_uploader(
        "Excel dosyasını seçin",
        type=["xlsx"],
        help=(
            "Sipariş listesinin bulunduğu "
            ".xlsx dosyasını seçin."
        )
    )

    if uploaded_file is not None:

        st.write(
            f"📄 Seçilen dosya: **{uploaded_file.name}**"
        )

        # -----------------------------------------------------
        # EXCEL'İ KONTROL ET
        # -----------------------------------------------------
        valid, error_message = validate_excel_file(
            uploaded_file
        )

        if not valid:

            st.error(
                "❌ Bu dosya sipariş Excel'i olarak "
                "uygun görünmüyor."
            )

            st.warning(
                f"Detay: {error_message}"
            )

            st.stop()

        st.success(
            "✅ Excel dosyası uygun görünüyor."
        )

        st.markdown(
            "Dosyadaki siparişler veritabanına aktarılacak "
            "(artık dosya olarak saklanmıyor)."
        )

        if st.button(
            "🚀 Sistemi Aç",
            type="primary",
            use_container_width=True
        ):

            try:

                # YENİ: dosya yerine doğrudan veritabanına aktarılıyor
                import_excel_to_db(
                    uploaded_file.getvalue(),
                    uploaded_by=current_username(),
                )

                # Cache'i temizle
                st.cache_data.clear()

                st.success(
                    "✅ Siparişler veritabanına aktarıldı."
                )

                time.sleep(0.5)

                st.rerun()

            except Exception as e:

                st.error(
                    f"❌ Excel kaydedilemedi: {e}"
                )

                st.stop()

    st.stop()
