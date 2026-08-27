"""
scripts/migrate_legacy_to_db.py
----------------------------------
BİR KEZ çalıştırılacak geçiş script'i: eski
gercek_siparisler.xlsx + araya_siparisler.json +
siparis_durumlari.json + iptal_siparisler.json dosyalarını okuyup
yeni veritabanı tablolarına aktarır.

Kullanım:
    export DATABASE_URL="postgresql+psycopg2://kullanici:sifre@sunucu:5432/siparis_takip"
    python scripts/migrate_legacy_to_db.py

Notlar:
- Script idempotent DEĞİLDİR: iki kez çalıştırılırsa siparişler
  ikinci bir "batch" olarak tekrar eklenir. Sadece BİR KEZ,
  eski sistemden yeni sisteme geçerken çalıştırın.
- Eski dosyalar (gercek_siparisler.xlsx, *.json) bu script
  tarafından SİLİNMEZ; elle silmek/arşivlemek isteyene bırakılır.
"""

import json
import os
import sys

# Proje kökünü import path'ine ekle (script scripts/ altında olduğu için)
sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

import pandas as pd  # noqa: E402

from infra.config import (  # noqa: E402
    LEGACY_EXCEL_FILE,
    LEGACY_STATE_FILE,
    LEGACY_STATUS_FILE,
    LEGACY_CANCELLED_FILE,
    SHEET_NAME,
)
from infra.db import init_db, session_scope  # noqa: E402
from infra.audit import write_audit_log  # noqa: E402
from infra.models import (  # noqa: E402
    Order,
    ProductionStatus,
    Insertion,
    CancelledOrder,
)
from core.domain.types import REQUIRED_COLUMNS  # noqa: E402
from core.domain.rules import normalize_order_id  # noqa: E402


def migrate_orders() -> int:

    if not os.path.exists(LEGACY_EXCEL_FILE):
        print(f"  - {LEGACY_EXCEL_FILE} bulunamadı, siparişler atlanıyor.")
        return 0

    import uuid
    from datetime import datetime

    df = pd.read_excel(LEGACY_EXCEL_FILE, sheet_name=SHEET_NAME, engine="openpyxl")
    df.columns = [str(c).strip() for c in df.columns]

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Excel'de eksik sütun(lar): {', '.join(missing)}")

    df = df[REQUIRED_COLUMNS].copy()
    df["Due Date"] = pd.to_datetime(df["Due Date"], errors="coerce")

    batch_id = str(uuid.uuid4())
    now = datetime.utcnow()

    rows = [
        Order(
            batch_id=batch_id,
            sales_order=str(row["Sales Order"]),
            normalized_sales_order=normalize_order_id(row["Sales Order"]),
            sort_name=str(row.get("Sort Name", "") or ""),
            item_number=str(row.get("Item Number", "") or ""),
            item_description=str(row.get("Item Description", "") or ""),
            quantity_ordered=row.get("Quantity Ordered"),
            due_date=None if pd.isna(row["Due Date"]) else row["Due Date"].to_pydatetime(),
            remarks=str(row.get("Remarks", "") or ""),
            is_current=True,
            uploaded_by="migration",
            uploaded_at=now,
        )
        for _, row in df.iterrows()
    ]

    with session_scope() as db:
        db.add_all(rows)
        write_audit_log(
            db,
            entity_type="orders", entity_id=batch_id, action="import",
            new_value=f"{len(rows)} satır",
            detail={"row_count": len(rows), "source": "legacy_migration"},
            performed_by="migration",
        )

    return len(rows)


def migrate_status() -> int:

    if not os.path.exists(LEGACY_STATUS_FILE):
        print(f"  - {LEGACY_STATUS_FILE} bulunamadı, durumlar atlanıyor.")
        return 0

    with open(LEGACY_STATUS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        return 0

    count = 0
    with session_scope() as db:
        for order_id, stage in data.items():
            if not isinstance(stage, (int, float)):
                continue
            db.add(ProductionStatus(
                normalized_sales_order=str(order_id),
                completed_stage=int(stage),
                updated_by="migration",
            ))
            count += 1

    return count


def migrate_insertions() -> int:

    if not os.path.exists(LEGACY_STATE_FILE):
        print(f"  - {LEGACY_STATE_FILE} bulunamadı, araya eklenenler atlanıyor.")
        return 0

    with open(LEGACY_STATE_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        return 0

    count = 0
    with session_scope() as db:
        for item in data:
            if not isinstance(item, dict):
                continue
            row = item.get("row", {})
            so = str(row.get("Sales Order", "")).strip()
            if not so:
                continue
            db.add(Insertion(
                id=str(item.get("id") or __import__("uuid").uuid4()),
                target_order=str(item.get("target_order", "")),
                normalized_target_order=normalize_order_id(item.get("target_order", "")),
                position=item.get("position", "before"),
                row=row,
                normalized_sales_order=normalize_order_id(so),
                created_by=item.get("created_by", ""),
            ))
            count += 1

    return count


def migrate_cancelled() -> int:

    if not os.path.exists(LEGACY_CANCELLED_FILE):
        print(f"  - {LEGACY_CANCELLED_FILE} bulunamadı, iptaller atlanıyor.")
        return 0

    with open(LEGACY_CANCELLED_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        return 0

    count = 0
    with session_scope() as db:
        for order_id in data:
            db.add(CancelledOrder(
                normalized_sales_order=normalize_order_id(order_id),
                cancelled_by="migration",
            ))
            count += 1

    return count


def main() -> None:

    print("Veritabanı tabloları hazırlanıyor...")
    init_db()

    print("Siparişler aktarılıyor (Excel -> orders)...")
    print(f"  -> {migrate_orders()} sipariş aktarıldı.")

    print("Üretim durumları aktarılıyor (JSON -> production_status)...")
    print(f"  -> {migrate_status()} durum aktarıldı.")

    print("Araya eklenen siparişler aktarılıyor (JSON -> insertions)...")
    print(f"  -> {migrate_insertions()} araya eklenen sipariş aktarıldı.")

    print("İptal edilen siparişler aktarılıyor (JSON -> cancelled_orders)...")
    print(f"  -> {migrate_cancelled()} iptal aktarıldı.")

    print("\n✅ Geçiş tamamlandı.")


if __name__ == "__main__":
    main()
