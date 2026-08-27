# 🧪 Production Tracker — Database Prototype (v1)

> ⚠️ **DİKKAT: DENEYSEL PROTOTİP (EXPERIMENTAL BUILD)**
> Bu dizindeki kod tabanı, dosya tabanlı (JSON) veri kalıcılığı mimarisinden **merkezi ilişkisel veritabanı (SQLite)** mimarisine geçişin ilk çalışan prototipidir.
> Kök dizindeki kararlı dosya tabanlı sürümden bağımsız olarak test ve geliştirme amacıyla izole edilmiştir.

---

## 🎯 Prototipin Amacı ve Kapsamı

Uygulamanın çok kullanıcılı ortamda (tabletler, operatör terminalleri, planlama ekranları) aynı anda çalışırken yaşadığı dosya kilitleme (file locking), veri senkronizasyonu gecikmeleri ve veri tutarsızlığı risklerini çözmek için geliştirilmiştir.

* **Eşzamanlı Erişim (Concurrency):** SQLite **WAL (Write-Ahead Logging)** modu ile eşzamanlı okuma/yazma desteği.
* **Katmanlı Mimari:** Repository katmanındaki tüm dosya I/O operasyonlarının parametrize SQL sorgularına dönüştürülmesi.
* **Otomatik Göç (Data Migration):** Eski JSON dosyalarındaki verilerin (users.json, order_statuses.json, insertions.json, cancelled_orders.json, audit_log.json) ilk çalıştırmada otomatik olarak SQLite tablolarına aktarılması.

---

## 🧱 Veritabanı Şeması (data/production.db)

Veritabanı başlatıldığında otomatik olarak şu tablolar oluşturulur ve indekslenir:

| Tablo Adı | Birincil Anahtar | Açıklama |
| :--- | :--- | :--- |
| users | username | Kullanıcı kimlik bilgileri, SHA-256 şifre hash\'leri, roller, aktiflik ve son giriş tarihi (last_login_at). |
| order_statuses | sales_order | Siparişlerin istasyon bazlı durumları (Dikiş, Boya, Serigrafi, Sevk vb.) ve son güncelleme zaman damgası. |
| insertions | id | Araya eklenen acil siparişlerin hedef sipariş numarası, konumu (before/after) ve satır JSON verisi. |
| cancelled_orders | sales_order | İptal edilen sipariş kayıtları, iptal eden kullanıcı ve zamanı. |
| audit_logs | id (Auto-inc) | Sistem genelinde yapılan tüm kritik işlemlerin denetim kaydı. |

---

## 🛠️ Mimari Değişiklikler ve İyileştirmeler

* **infra/db.py:** Bağlantı havuzu ve bağlam yöneticisi (db_session), WAL modu optimizasyonu, PRAGMA ayarları ve otomatik migrasyon motoru.
* **infra/audit.py & core/repositories/audit_repository.py:** Tüm CRUD işlemlerinin (acil sipariş ekleme/çıkarma, aşama onayları, kullanıcı rolleri) denetim kaydına asenkron/hataya dayanıklı bağlanması.
* **ui/auth.py:** SQLite repository ile tam senkronize rol tabanlı yetkilendirme sistemi.
* **Anti-Flicker & Sekme Optimizasyonu (app.py):**
  * 5 saniyelik otomatik canlı yenilemeler sırasında tarayıcı sekme başlığının ve favicon durumunun sürekli yükleme animasyonuna girmesini engelleyen JS/CSS motoru.
  * Eski iOS/Safari sürümleri için Array.prototype.at polyfill entegrasyonu.
  * Sekmeler arası geçişte veri kaybını önleyen main_active_tab oturum yönetimi.

---

## 🚀 Prototipi Çalıştırma

Prototip klasörünü bağımsız olarak test etmek için:

1. Prototip dizinine geçiş: `cd production_tracker_databasePrototype1`
2. Önbellek temizliği: `Get-ChildItem -Path . -Filter '__pycache__' -Recurse | Remove-Item -Recurse -Force`
3. Çalıştırma: `streamlit run app.py`
