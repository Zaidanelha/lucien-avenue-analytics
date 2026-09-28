"""Konfigurasi terpusat. Semua nilai bisa di-override lewat file .env."""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

DATA_DIR = BASE_DIR / "data"
REPORT_DIR = DATA_DIR / "reports"
SQL_DIR = BASE_DIR / "sql"

# Default: SQLite (tanpa instalasi apa pun). Bisa diganti ke MySQL, contoh:
# SOURCE_DB_URL=mysql+pymysql://root:@localhost:3306/lucien_source
SOURCE_DB_URL = os.getenv("SOURCE_DB_URL", f"sqlite:///{(DATA_DIR / 'source.db').as_posix()}")
WAREHOUSE_DB_URL = os.getenv("WAREHOUSE_DB_URL", f"sqlite:///{(DATA_DIR / 'warehouse.db').as_posix()}")

# Parameter generator data sintetis
START_DATE = os.getenv("START_DATE", "2024-01-01")
END_DATE = os.getenv("END_DATE", "2025-12-31")
N_CUSTOMERS = int(os.getenv("N_CUSTOMERS", "10000"))
BASE_DAILY_ORDERS = float(os.getenv("BASE_DAILY_ORDERS", "35"))
RANDOM_SEED = int(os.getenv("RANDOM_SEED", "42"))
