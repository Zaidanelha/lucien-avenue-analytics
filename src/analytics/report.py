"""Menjalankan semua query analitik di sql/analytics dan menyimpan hasilnya ke CSV."""
import logging

import pandas as pd
from sqlalchemy import text

import config
from src.db import get_engine, read_sql_file

log = logging.getLogger(__name__)

KPI_QUERY = """
SELECT COUNT(DISTINCT order_id)                      AS total_orders,
       COUNT(DISTINCT customer_key)                  AS active_customers,
       SUM(net_amount)                               AS revenue,
       SUM(net_amount) / COUNT(DISTINCT order_id)    AS avg_order_value
FROM fact_sales
WHERE order_status = 'selesai'
"""


def run_reports() -> dict[str, pd.DataFrame]:
    engine = get_engine(config.WAREHOUSE_DB_URL)
    config.REPORT_DIR.mkdir(parents=True, exist_ok=True)

    with engine.connect() as conn:
        kpi = pd.read_sql(text(KPI_QUERY), conn).iloc[0]
    log.info("KPI utama (pesanan selesai): %s pesanan | %s pelanggan aktif | revenue Rp %s | AOV Rp %s",
             f"{int(kpi.total_orders):,}", f"{int(kpi.active_customers):,}",
             f"{kpi.revenue:,.0f}", f"{kpi.avg_order_value:,.0f}")

    results = {}
    for sql_file in sorted((config.SQL_DIR / "analytics").glob("*.sql")):
        df = read_sql_file(engine, sql_file)
        df.to_csv(config.REPORT_DIR / f"{sql_file.stem}.csv", index=False)
        results[sql_file.stem] = df
        preview = df.head(12).to_string(index=False)
        log.info("\n=== %s (%d baris) ===\n%s", sql_file.stem, len(df), preview)
    log.info("Laporan CSV tersimpan di %s", config.REPORT_DIR)
    return results
