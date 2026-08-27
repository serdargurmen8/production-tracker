"""
core/domain/types.py
---------------------
Saf domain sabitleri: hiçbir I/O, hiçbir Streamlit çağrısı
içermez. Sadece "iş kuralı" niteliğindeki sabit veriler.
"""

# Her sipariş sırayla bu 6 aşamadan geçer: Dikiş -> Boya ->
# Serigrafi -> Sevkiyat -> İrsaliye -> Sevk. Aşamalar rastgele
# işaretlenemez; her biri bir öncekine bağlıdır (sıra atlanamaz).

STATUS_STAGES = [
    "Dikiş",
    "Boya",
    "Serigrafi",
    "Sevkiyat",
    "İrsaliye",
    "Sevk",
]

# Sarıdan yeşile, birbirinden belirgin şekilde ayrışan ama göze
# batmayan (pastel/soft) 6 renk. STATUS_STAGES ile aynı sırada.

# Sarıdan yeşile, göze batmayan (soluk/pastel) 6 renk.
# 1 aşama tamamlanınca en soluk sarı, 6 aşama (hepsi) tamamlanınca
# en yumuşak yeşil kullanılır.
# Sarıdan yeşile giden, birbirinden belirgin şekilde AYRIŞAN
# ama yine de göze batmayan (pastel/soft) 6 renk. Sadece tonu
# (hue) kaydırmak yerine doygunluk/parlaklık da hafifçe
# değiştirilerek aşamalar arasındaki fark daha net kılındı.
STATUS_COLORS = [
    "hsl(50, 100%, 50%)",  # 0) Sarı       - Canlı Tatlı Sarı (Düzeltildi)
    "hsl(220, 80%, 55%)",  # 1) Poor       - Açık/Orta Mavi (Yumuşatıldı)
    "hsl(195, 100%, 45%)", # 2) Fair       - Açık Mavi / Turkuaz
    "hsl(0, 0%, 100%)",    # 3) Good       - Beyaz
    "hsl(75, 85%, 45%)",   # 4) Very Good  - Fıstık Yeşili
    "hsl(135, 60%, 38%)",  # 5) Excellent  - Açık/Canlı Yeşil (Açıldı)
]

# Ana sipariş Excel'inde bulunması zorunlu sütunlar
# =============================================================
# GEREKLİ EXCEL SÜTUNLARI
# =============================================================
REQUIRED_COLUMNS = [
    "Sales Order",
    "Sort Name",
    "Item Number",
    "Item Description",
    "Quantity Ordered",
    "Due Date",
    "Remarks",
]
