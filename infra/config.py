"""
infra/config.py
----------------
Uygulamanın tüm bağlantı ayarları, ortam değişkenleri ve sabit
değerleri. Diğer hiçbir modül bu dosyanın dışına path/env
mantığı koymamalı; bir ayarın nereden geldiğini değiştirmek
istediğinde tek bakılacak yer burası olmalı.
"""

import os

# Uygulamanın bulunduğu klasör (app.py'nin bulunduğu proje kökü).
BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

SHEET_NAME = 0

REFRESH_MS = 5_000

# =================================================================
# VERİ DOSYALARI (Excel + JSON) — dosya sistemi tabanlı depolama
# -----------------------------------------------------------------
# Veritabanı (PostgreSQL/SQL Server) kaldırıldı; sipariş verisi,
# üretim durumları, araya eklenen acil siparişler, iptal edilen
# siparişler, kullanıcılar ve denetim kayıtları artık bu dosyalarda
# tutulur. Eşzamanlı yazmalar infra/storage.py içindeki FileLock
# ile korunur.
# =================================================================
DATA_DIR = os.path.join(BASE_DIR, "data")

ORDERS_FILE = os.path.join(BASE_DIR, "gercek_siparisler.xlsx")
STATUS_FILE = os.path.join(DATA_DIR, "siparis_durumlari.json")
INSERTIONS_FILE = os.path.join(DATA_DIR, "araya_siparisler.json")
CANCELLED_FILE = os.path.join(DATA_DIR, "iptal_siparisler.json")
USERS_FILE = os.path.join(DATA_DIR, "kullanicilar.json")
AUDIT_LOG_FILE = os.path.join(DATA_DIR, "audit_log.json")

# Yeni excel yüklendiğinde bir önceki günün excel'i buraya
# arşivlenir (eski excel_arsiv/ klasörünün davranışı).
EXCEL_ARCHIVE_DIR = os.path.join(BASE_DIR, "excel_arsiv")

# Geriye dönük uyumluluk: scripts/migrate_legacy_to_db.py bu isimleri
# referans alıyordu. Script artık kullanılmıyor ama silinmedi;
# burada aynı isimler yeni dosya yollarına işaret eder.
LEGACY_EXCEL_FILE = ORDERS_FILE
LEGACY_STATE_FILE = INSERTIONS_FILE
LEGACY_STATUS_FILE = STATUS_FILE
LEGACY_CANCELLED_FILE = CANCELLED_FILE

# --- Kullanıcı sistemi kurulum (bootstrap) anahtarı ---
# Artık uygulama kişi bazlı kullanıcı adı/şifre ile çalışıyor
# (bkz. core/repositories/user_repository.py, ui/auth.py). Bu
# değişken SADECE veritabanında HİÇ kullanıcı yokken ilk ADMIN
# hesabını oluşturmak için bir kerelik "kurulum anahtarı" olarak
# kullanılır; sıradan girişlerde kullanılmaz. İlk admin hesabı
# oluşturulduktan sonra bu anahtarın bir önemi kalmaz - üretimde
# yine de ortam değişkeni olarak ayarlanması ve varsayılanın
# KULLANILMAMASI önerilir:
#   Windows:  set SETUP_KEY=gercekbirsifre
#   Linux:    export SETUP_KEY=gercekbirsifre
SETUP_KEY = os.environ.get(
    "SETUP_KEY",
    os.environ.get("MASTER_PASSWORD", "Mauser2026!!"),
)

# --- YENİ: Yüklenen excel'lerin arşivlendiği klasör ---
ARCHIVE_DIR = os.path.join(
    BASE_DIR,
    "excel_arsiv"
)
