"""Helper database yang dipakai generator, ETL, laporan, dan dashboard."""
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

import config


def get_engine(url: str) -> Engine:
    """Membuat koneksi SQLAlchemy. Untuk SQLite, folder data dibuat otomatis."""
    if url.startswith("sqlite"):
        config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    return create_engine(url)


def _split_statements(sql: str) -> list[str]:
    """Memecah isi file .sql menjadi statement terpisah (abaikan komentar --)."""
    lines = [ln for ln in sql.splitlines() if not ln.strip().startswith("--")]
    return [stmt.strip() for stmt in "\n".join(lines).split(";") if stmt.strip()]


def run_sql_file(engine: Engine, path: Path) -> None:
    """Menjalankan semua statement DDL di sebuah file .sql dalam satu transaksi."""
    statements = _split_statements(Path(path).read_text(encoding="utf-8"))
    with engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))


def write_df(df: pd.DataFrame, table: str, engine: Engine) -> int:
    """Menulis DataFrame ke tabel yang sudah dibuat (append), dalam batch."""
    if df.empty:
        return 0
    df.to_sql(table, con=engine, if_exists="append", index=False, chunksize=1000, method="multi")
    return len(df)


def read_sql_file(engine: Engine, path: Path) -> pd.DataFrame:
    """Menjalankan satu query SELECT dari file .sql dan mengembalikan DataFrame."""
    query = Path(path).read_text(encoding="utf-8")
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn)
