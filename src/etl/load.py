"""Tahap LOAD: menulis star schema dan log audit ke data warehouse."""
import logging

import pandas as pd
from sqlalchemy.engine import Engine

import config
from src.db import run_sql_file, write_df

log = logging.getLogger(__name__)


def prepare_audit_tables(engine: Engine) -> None:
    run_sql_file(engine, config.SQL_DIR / "warehouse_audit.sql")


def load_star_schema(engine: Engine, tables: dict[str, pd.DataFrame]) -> dict[str, int]:
    """Full refresh: skema dibuat ulang lalu dimensi dimuat lebih dulu, baru tabel fakta
    (urutan ini penting karena fakta mereferensikan dimensi lewat foreign key)."""
    run_sql_file(engine, config.SQL_DIR / "warehouse_schema.sql")
    counts = {}
    for name in ["dim_date", "dim_customer", "dim_product", "fact_sales"]:
        counts[name] = write_df(tables[name], name, engine)
        log.info("  load    %-12s %8s baris", name, f"{counts[name]:,}")
    return counts


def write_audit(engine: Engine, run_log: dict, dq_frame: pd.DataFrame,
                quarantine: pd.DataFrame | None = None) -> None:
    """Menyimpan log run, hasil data quality, dan baris yang dikarantina (untuk ditelusuri)."""
    write_df(pd.DataFrame([run_log]), "etl_run_log", engine)
    write_df(dq_frame, "data_quality_log", engine)
    if quarantine is not None and not quarantine.empty:
        cols = ["barang_pesanan_id", "pesanan_id", "produk_id", "harga", "quantity"]
        q = quarantine[cols].copy()
        q.insert(0, "run_id", run_log["run_id"])
        q["reason"] = "quantity/harga <= 0"
        write_df(q, "quarantine_order_items", engine)
