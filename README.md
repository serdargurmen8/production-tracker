# Sipariş Takip - Canlı Ekran

## Klasör yapısı

```
siparis_takip/
├── app.py                          # Giriş noktası (streamlit run app.py)
├── infra/
│   ├── config.py                    # Tüm env değişkenleri, sabit ayarlar (DATABASE_URL dahil)
│   ├── db.py                        # SQLAlchemy engine / session (transaction yönetimi)
│   └── models.py                    # ORM tabloları: orders, production_status,
│                                     # insertions, cancelled_orders, users, audit_logs
├── core/
│   ├── domain/
│   │   ├── types.py                 # STATUS_STAGES, STATUS_COLORS, REQUIRED_COLUMNS
│   │   └── rules.py                 # normalize_order_id, apply_insertions,
│   │                                 # compute_status, _row_bg_color (saf iş kuralları)
│   ├── repositories/
│   │   ├── excel_repository.py      # Excel okuma/doğrulama + veritabanına aktarma
│   │   ├── insertions_repository.py # "Araya eklenen" acil siparişler (DB)
│   │   ├── cancelled_repository.py  # İptal edilen siparişler (DB)
│   │   └── status_repository.py     # Üretim aşaması takibi (DB)
│   ├── services/
│   │   └── pdf_service.py           # generate_pdf / clean_text
│   └── use_cases/
│       ├── html_builder.py          # "İş emri kartı" HTML tablo üretimi
│       ├── live_screen.py           # Canlı Ekran sekmesi (herkes görür)
│       └── planning_screen.py       # Planlama / acil sipariş sekmesi (sadece yönetici)
├── ui/
│   ├── auth.py                      # Yönetici giriş/çıkış formu (sidebar)
│   └── setup_screens.py             # İlk kurulum + günlük excel güncelleme ekranları
└── scripts/
    └── migrate_legacy_to_db.py      # Eski Excel/JSON dosyalarını bir kerelik DB'ye aktarır
```
streamlit --version == 1.28 kullanımına uygundur.

## 🗄️ Veritabanı (Excel + JSON yerine)

Sipariş verisi, üretim durumları, araya eklenen acil siparişler ve
iptal edilen siparişler artık dosya sisteminde değil, **PostgreSQL**
(veya SQL Server) üzerinde tutulur:

```
Tablet 1 ─┐
Tablet 2 ─┤
Tablet 3 ─┼──► PostgreSQL / SQL Server
Tablet 4 ─┘
```

| Eski dosya                  | Yeni tablo           |
|------------------------------|-----------------------|
| `gercek_siparisler.xlsx`     | `orders`              |
| `siparis_durumlari.json`     | `production_status`   |
| `araya_siparisler.json`      | `insertions`          |
| `iptal_siparisler.json`      | `cancelled_orders`     |
| *(yoktu)*                    | `users` *(ileride kişi bazlı giriş için)* |
| *(yoktu)*                    | `audit_logs` *(kim, ne zaman, neyi değiştirdi)* |

Excel hâlâ **günlük veri girişi formatı** olarak kullanılır (ERP'den
excel çıktısı almak değişmedi); tek fark, yüklenen excel dosyanın
artık diske değil doğrudan veritabanına yazılmasıdır. Önceki gün
girilen siparişler silinmez, `orders.is_current = false` yapılarak
arşivlenir (eski `excel_arsiv/` klasörünün yerini alır).

### Kurulum

1. Bir PostgreSQL veritabanı oluşturun ve bağlantı bilgisini
   ortam değişkeni olarak ayarlayın:

   ```bash
   export DATABASE_URL="postgresql+psycopg2://kullanici:sifre@sunucu:5432/siparis_takip"
   ```

   (SQL Server kullanmak isterseniz: `mssql+pyodbc://kullanici:sifre@sunucu/siparis_takip?driver=ODBC+Driver+17+for+SQL+Server`)

2. Uygulamayı çalıştırın; tablolar ilk açılışta otomatik oluşturulur
   (`infra/db.py` içindeki `init_db()`, `app.py` tarafından her
   başlangıçta çağrılır — idempotenttir, var olan tabloları bozmaz).

3. **Eski sistemden geçiyorsanız**, eski `gercek_siparisler.xlsx` ve
   `.json` dosyalarınızı proje köküne koyup bir kereliğine şunu
   çalıştırın:

   ```bash
   export DATABASE_URL="postgresql+psycopg2://kullanici:sifre@sunucu:5432/siparis_takip"
   python scripts/migrate_legacy_to_db.py
   ```

   Bu script eski verileri okuyup ilgili tablolara aktarır. Script
   idempotent değildir; sadece bir kez çalıştırın.

### Neden bu değişiklik gerekliydi?

Birden fazla tablet/kullanıcı aynı anda Excel + JSON dosyalarını
değiştirdiğinde dosya kilitleri, eşzamanlı yazma çakışmaları, veri
kaybı ve dosya bozulması riskleri oluşuyordu. `FileLock` bunu
kısmen azaltıyordu ama Excel'i gerçek bir veritabanına dönüştürmüyordu.
PostgreSQL'e geçişle birlikte:
- Her satır/kayıt kendi transaction'ı içinde güvenle güncellenir,
- Aynı siparişe aynı anda yazan işlemler veritabanı seviyesinde
  otomatik sıraya girer (satır bazlı kilitleme), farklı siparişler
  birbirini beklemez,
- Tüm değişiklikler `audit_logs` tablosunda izlenebilir hâle gelir.

## Çalıştırma

```bash
cd siparis_takip
pip install -r requirements.txt
export DATABASE_URL="postgresql+psycopg2://kullanici:sifre@sunucu:5432/siparis_takip"
streamlit run "app.py dosyasının yolu"
```

`SETUP_KEY` ortam değişkenini ayarlamayı unutmayın; ayarlamazsanız
kod içindeki test amaçlı varsayılan anahtar kullanılır. `SETUP_KEY`
sadece veritabanında HİÇ kullanıcı yokken ilk yönetici (ADMIN)
hesabını oluşturmak için bir kerelik kurulum anahtarıdır — eskiden
herkesin paylaştığı `MASTER_PASSWORD`'ün yerini aldı. İlk ADMIN
hesabı oluşturulduktan sonra herkes kendi kullanıcı adı/şifresiyle
giriş yapar (bkz. "Kullanıcı Yönetimi" sekmesi); rollerin neye
izin verdiği `core/domain/permissions.py` içinde tanımlıdır.

## Neden bu bölünme?

- **domain**: Hiçbir I/O yapmayan, saf veri/kural fonksiyonları — test etmesi en kolay katman.
- **repositories**: Sadece "veriyi nereden okuyup nereye yazıyoruz" ile ilgilenir.
- **services**: Tek başına anlamlı, yeniden kullanılabilir iş parçaları (örn. PDF üretimi).
- **use_cases**: Bir ekranın uçtan uca senaryosunu yürütür (repository + domain + service'leri bir araya getirir).
- **ui**: Streamlit'e özgü, tekrar kullanılabilir küçük ekran parçaları (giriş formu, kurulum ekranı).
- **infra**: "Bu dosya nerede duruyor / bu ayar ne" sorularının tek cevabı.
