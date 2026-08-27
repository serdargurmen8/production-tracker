"""
app.py
--------
Uygulama giriş noktası. 
iPad/Safari Array.at polyfill desteği, sekme optimizasyonu ve 
sekme titremesini (tab flicker) engelleyen anti-flicker motoru içerir.
"""

import streamlit as st
import streamlit.components.v1 as components

from infra.db import init_database
init_database()

from core.repositories.excel_repository import (
    read_main_excel,
    has_orders,
    get_last_upload_time,
)
from core.repositories.insertions_repository import load_insertions
from core.repositories.user_repository import has_any_user
from ui.auth import (
    init_auth_session_state,
    is_authenticated,
    can,
    render_login,
    render_first_admin_setup,
)
from ui.setup_screens import render_daily_excel_uploader, excel_selection_screen
from ui.user_management import render_user_management_tab
from ui.audit_log import render_audit_log_tab
from core.use_cases.live_screen import render_live_screen
from core.use_cases.planning_screen import render_planning_tab

# =============================================================
# AYARLAR
# =============================================================
st.set_page_config(
    page_title="Sipariş Takip - Canlı Ekran",
    layout="wide"
)

# 1. Anti-Flicker CSS: Streamlit yükleme widget'ını ve progress bar'ı gizler
st.markdown("""
<style>
    /* Streamlit durum widget'ını gizle */
    div[data-testid="stStatusWidget"] {
        visibility: hidden !important;
        display: none !important;
    }
    /* Üstteki kırmızı/renkli yükleme çizgisini gizle */
    .stProgress > div > div > div > div {
        display: none !important;
    }
    header[data-testid="stHeader"] {
        background-color: transparent !important;
    }
</style>
""", unsafe_allow_html=True)

# 2. Anti-Flicker JS + iPad Safari Array.at Polyfill
components.html(
    """
    <script>
    (function() {
        [window.parent, window.top, window].forEach(function(w) {
            try {
                if (w && w.Array && !w.Array.prototype.at) {
                    w.Array.prototype.at = function(n) {
                        n = Math.trunc(n) || 0;
                        if (n < 0) n += this.length;
                        if (n < 0 || n >= this.length) return undefined;
                        return this[n];
                    };
                }
                if (w && w.String && !w.String.prototype.at) {
                    w.String.prototype.at = function(n) {
                        n = Math.trunc(n) || 0;
                        if (n < 0) n += this.length;
                        if (n < 0 || n >= this.length) return undefined;
                        return this[n];
                    };
                }
                // Sekmedeki sürekli yanıp sönen yükleme durumunu (Flicker) dondurur
                if (w && w.document) {
                    var fixedTitle = "Sipariş Takip - Canlı Ekran";
                    w.document.title = fixedTitle;
                    Object.defineProperty(w.document, 'title', {
                        set: function() {},
                        get: function() { return fixedTitle; }
                    });
                }
            } catch(e) {}
        });
    })();
    </script>
    """,
    height=0,
    width=0,
)

# =============================================================
# SESSION STATE BAŞLANGIÇ DEĞERLERİ
# =============================================================
init_auth_session_state()

# =============================================================
# KULLANICI SİSTEMİ / GİRİŞ
# =============================================================
if not has_any_user():
    render_first_admin_setup()

render_login()

if not is_authenticated():
    st.info(
        "📋 Sisteme erişmek için lütfen soldaki menüden giriş yapın. "
        "Hesabınız yoksa yöneticinizden sizin için bir hesap "
        "oluşturmasını isteyin."
    )
    st.stop()

# =============================================================
# SİPARİŞ KONTROLÜ
# =============================================================
if not has_orders():
    if can("excel_upload"):
        excel_selection_screen()
    else:
        st.info(
            "📋 Sistem henüz kurulmadı. "
            "Lütfen yöneticinin excel yüklemesini bekleyin."
        )
        st.stop()

# =============================================================
# GÜNLÜK EXCEL GÜNCELLEME ALANI
# =============================================================
if can("excel_upload"):
    render_daily_excel_uploader()

# =============================================================
# ROLE GÖRE SEKMELER
# =============================================================
show_planning_tab = can("urgent_order") or can("cancel_order")
show_user_management_tab = can("user_management")
show_audit_log_tab = can("view_audit_log")

tab_labels = ["📺 Canlı Ekran"]
if show_planning_tab:
    tab_labels.append("⚡ Araya Acil Sipariş Ekle/Çıkar")
if show_user_management_tab:
    tab_labels.append("👥 Kullanıcı Yönetimi")
if show_audit_log_tab:
    tab_labels.append("🧾 Denetim Kaydı")

if len(tab_labels) == 1:
    main_df = read_main_excel()
    insertions = load_insertions()
    mtime = get_last_upload_time()
    render_live_screen(main_df, insertions, mtime)
else:
    selected_tab = st.radio(
        "Menü",
        tab_labels,
        horizontal=True,
        label_visibility="collapsed",
        key="main_active_tab"
    )
    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

    if selected_tab == "📺 Canlı Ekran":
        main_df = read_main_excel()
        insertions = load_insertions()
        mtime = get_last_upload_time()
        render_live_screen(main_df, insertions, mtime)

    elif selected_tab == "⚡ Araya Acil Sipariş Ekle/Çıkar":
        main_df = read_main_excel()
        insertions = load_insertions()
        render_planning_tab(main_df, insertions)

    elif selected_tab == "👥 Kullanıcı Yönetimi":
        render_user_management_tab()

    elif selected_tab == "🧾 Denetim Kaydı":
        render_audit_log_tab()
