"""Pencatatan hasil pemeriksaan kualitas data (data quality) selama ETL.

Ada dua jenis pemeriksaan:
- WARNING/INFO : masalah yang bisa diperbaiki otomatis (dicatat, pipeline lanjut).
- ERROR        : pelanggaran integritas (mis. key duplikat); pipeline DIHENTIKAN
                 agar data yang salah tidak masuk ke warehouse.
"""
import logging
from dataclasses import dataclass, field

import pandas as pd

log = logging.getLogger(__name__)


class DataQualityError(Exception):
    """Dilempar ketika pemeriksaan integritas gagal."""


@dataclass
class QualityReport:
    results: list[dict] = field(default_factory=list)

    def add(self, check: str, table: str, failed_rows: int, total_rows: int,
            action: str, severity: str = "WARNING") -> None:
        self.results.append({
            "check_name": check, "table_name": table, "severity": severity if failed_rows else "PASS",
            "failed_rows": int(failed_rows), "total_rows": int(total_rows),
            "failed_pct": round(100 * failed_rows / total_rows, 3) if total_rows else 0.0,
            "action_taken": action if failed_rows else "-",
        })
        level = logging.WARNING if failed_rows and severity != "INFO" else logging.INFO
        log.log(level, "  [DQ] %-45s %6d / %-7d -> %s", check, failed_rows, total_rows,
                action if failed_rows else "OK")

    def to_frame(self, run_id: str) -> pd.DataFrame:
        df = pd.DataFrame(self.results)
        df.insert(0, "run_id", run_id)
        return df

    @property
    def total_rejected(self) -> int:
        return sum(r["failed_rows"] for r in self.results if "dibuang" in r["action_taken"]
                   or "dihapus" in r["action_taken"] or "dikarantina" in r["action_taken"]
                   or "dikecualikan" in r["action_taken"])


def assert_integrity(dim_date: pd.DataFrame, dim_customer: pd.DataFrame,
                     dim_product: pd.DataFrame, fact: pd.DataFrame) -> None:
    """Pemeriksaan wajib sebelum load. Gagal = pipeline berhenti."""
    problems = []
    for name, df, key in [("dim_date", dim_date, "date_key"), ("dim_customer", dim_customer, "customer_key"),
                          ("dim_product", dim_product, "product_key"), ("fact_sales", fact, "order_item_id")]:
        if df[key].duplicated().any():
            problems.append(f"{name}.{key} tidak unik")
    if fact.empty:
        problems.append("fact_sales kosong")
    for col, dim, key in [("date_key", dim_date, "date_key"), ("customer_key", dim_customer, "customer_key"),
                          ("product_key", dim_product, "product_key")]:
        orphans = ~fact[col].isin(dim[key])
        if orphans.any():
            problems.append(f"{orphans.sum()} baris fact_sales.{col} tidak punya pasangan di dimensi")
    if (fact["net_amount"] < 0).any():
        problems.append("ada net_amount negatif")
    if problems:
        raise DataQualityError("; ".join(problems))
    log.info("  [DQ] Integrity check lolos (primary key unik, tidak ada orphan key)")
