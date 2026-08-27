# 🧪 Production Tracker - Database Prototype 1 (Deneysel)

> ⚠️ **DİKKAT: DENEYSEL PROTOTİPTİR**
> Bu klasördeki kodlar, dosya tabanlı JSON mimarisinden **SQLite (production.db) merkezi veritabanı** mimarisine geçişin ilk çalışan prototipidir (v1).
> Nihai/kararlı sürüm değildir; test ve referans amacıyla saklanmaktadır.

### Prototip Özellikleri:
* SQLite WAL modu ile eşzamanlı veri yazma desteği
* Otomatik JSON -> SQLite veri göçü (Migration)
* Rol tabanlı yetkilendirme ve denetim kaydı (Audit Log) entegrasyonu
* Canlı ekran anti-flicker (sekme başlığı titremesini önleme) yaması
