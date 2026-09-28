"""Tahap EXTRACT: membaca tabel mentah dari database sumber (OLTP)."""
import logging

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

log = logging.getLogger(__name__)

# Tabel yang diambil beserta kolom tanggal yang perlu di-parse
SOURCE_TABLES = {
    "users": ["tanggal_lahir", "created_at", "updated_at"],
    "products": ["tanggal_rilis", "created_at", "updated_at"],
    "orders": ["created_at", "updated_at"],
    "order_items": [],
    "payments": [],
    "shipments": ["perkiraan_pengiriman"],
    "returns": ["created_at", "updated_at"],
}


def extract(engine: Engine) -> dict[str, pd.DataFrame]:
    """Mengambil semua tabel sumber dan mengembalikannya sebagai dict of DataFrame."""
    raw = {}
    with engine.connect() as conn:
        for table, date_cols in SOURCE_TABLES.items():
            df = pd.read_sql(text(f"SELECT * FROM {table}"), conn)
            for col in date_cols:
                # errors="coerce": nilai tanggal yang rusak menjadi NaT, tidak menghentikan pipeline
                df[col] = pd.to_datetime(df[col], errors="coerce")
            raw[table] = df
            log.info("  extract %-12s %8s baris", table, f"{len(df):,}")
    return raw
