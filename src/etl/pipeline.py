"""Orkestrasi pipeline ETL: Extract -> Validate & Transform -> Load -> Audit log."""
import logging
import time
from datetime import date, datetime

import config
from src.db import get_engine
from src.etl import transform as tf
from src.etl.extract import extract
from src.etl.load import load_star_schema, prepare_audit_tables, write_audit
from src.etl.quality import QualityReport, assert_integrity

log = logging.getLogger(__name__)


def run_etl() -> dict:
    run_id = datetime.now().strftime("%Y%m%d%H%M%S%f")
    started_at, t0 = datetime.now(), time.perf_counter()
    source = get_engine(config.SOURCE_DB_URL)
    warehouse = get_engine(config.WAREHOUSE_DB_URL)
    prepare_audit_tables(warehouse)
    dq = QualityReport()
    rows_extracted = 0
    rejected_items = None

    try:
        # ---------------- EXTRACT ----------------
        log.info("[1/3] EXTRACT dari database sumber")
        raw = extract(source)
        rows_extracted = sum(len(df) for df in raw.values())
        users, products, orders = raw["users"], raw["products"], raw["orders"]
        items, payments = raw["order_items"], raw["payments"]
        shipments, returns = raw["shipments"], raw["returns"]
        snapshot_date = orders["created_at"].max().date()

        # ---------------- VALIDATE & TRANSFORM ----------------
        log.info("[2/3] VALIDATE & TRANSFORM")

        # Pelanggan
        raw_email = users["email"].astype("string")
        dq.add("Email tidak ternormalisasi (spasi/kapital)", "users",
               (raw_email != tf.normalize_email(raw_email)).sum(), len(users), "dinormalisasi (trim & lowercase)")
        raw_gender = users["jenis_kelamin"].astype("string")
        dq.add("Format jenis kelamin tidak standar", "users",
               (~raw_gender.isin(["Pria", "Wanita"])).sum(), len(users), "dipetakan ke Pria/Wanita/Tidak diketahui")
        city_token = users["alamat"].astype("string").str.split(",").str[-2].str.strip()
        clean_city = tf.extract_city(users["alamat"])
        dq.add("Penulisan kota tidak standar", "users",
               (city_token.notna() & (city_token != clean_city)).sum(), len(users), "distandarkan via tabel alias kota")
        dq.add("Alamat kosong", "users", users["alamat"].isna().sum(), len(users),
               "kota diisi 'Tidak diketahui'", severity="INFO")
        valid_birth = tf.clean_birth_date(users["tanggal_lahir"], snapshot_date)
        dq.add("Tanggal lahir tidak valid", "users",
               (users["tanggal_lahir"].notna() & valid_birth.isna()).sum(), len(users), "dikosongkan")

        internal = tf.is_internal_email(users["email"])
        internal_ids = set(users.loc[internal, "user_id"])
        dq.add("Akun internal/testing", "users", internal.sum(), len(users), "dikecualikan dari warehouse")
        internal_orders = orders["user_id"].isin(internal_ids)
        dq.add("Pesanan dari akun internal/testing", "orders", internal_orders.sum(), len(orders),
               "dikecualikan dari warehouse")
        orders_clean = orders[~internal_orders]

        # Produk
        dq.add("Penulisan brand tidak standar", "products",
               (products["brand"].astype("string") != tf.normalize_brand(products["brand"])).sum(),
               len(products), "dinormalisasi")
        dq.add("Kategori (jenis) produk kosong", "products", products["jenis"].isna().sum(),
               len(products), "diisi 'Lainnya'")

        # Pesanan & item
        dup_ids = set(tf.find_duplicate_orders(orders_clean, items))
        dq.add("Pesanan ganda (double submit < 60 detik)", "orders", len(dup_ids), len(orders_clean), "dihapus")
        orders_clean = orders_clean[~orders_clean["pesanan_id"].isin(dup_ids)]

        mismatch = tf.find_total_mismatch(orders_clean)
        dq.add("jumlah_total != subtotal - discount", "orders", len(mismatch), len(orders_clean),
               "nilai dihitung ulang dari item pesanan")

        valid_items, rejected_items = tf.split_valid_items(items[~items["pesanan_id"].isin(dup_ids)])
        dq.add("Quantity/harga item tidak valid (<= 0)", "order_items", len(rejected_items),
               len(valid_items) + len(rejected_items), "dikarantina (tidak dimuat)")

        orphan_items = ~valid_items["pesanan_id"].isin(orders["pesanan_id"])
        dq.add("Item tanpa pesanan induk (orphan)", "order_items", orphan_items.sum(), len(valid_items), "dibuang")
        valid_items = valid_items[~orphan_items]

        no_payment = ~orders_clean["pesanan_id"].isin(payments["pesanan_id"])
        dq.add("Pesanan tanpa data pembayaran", "orders", no_payment.sum(), len(orders_clean),
               "metode pembayaran = 'Tidak diketahui'", severity="INFO")

        # Star schema
        dim_date = tf.build_dim_date(orders_clean["created_at"].min().date(), snapshot_date)
        dim_customer = tf.build_dim_customer(users, snapshot_date)
        dim_product = tf.build_dim_product(products)
        fact = tf.build_fact_sales(orders_clean, valid_items, payments, shipments, returns,
                                   dim_customer, dim_product)
        assert_integrity(dim_date, dim_customer, dim_product, fact)

        # ---------------- LOAD ----------------
        log.info("[3/3] LOAD ke data warehouse")
        counts = load_star_schema(warehouse, {"dim_date": dim_date, "dim_customer": dim_customer,
                                              "dim_product": dim_product, "fact_sales": fact})
        status, message = "SUCCESS", "OK"
    except Exception as exc:  # dicatat ke log audit, lalu dilempar ulang
        counts, status, message = {"fact_sales": 0}, "FAILED", str(exc)[:500]
        log.error("ETL gagal: %s", exc)
        raise
    finally:
        duration = round(time.perf_counter() - t0, 2)
        run_log = {"run_id": run_id, "started_at": started_at, "finished_at": datetime.now(),
                   "status": status, "rows_extracted": rows_extracted,
                   "rows_rejected": dq.total_rejected, "rows_loaded_fact": counts.get("fact_sales", 0),
                   "duration_seconds": duration, "message": message}
        write_audit(warehouse, run_log, dq.to_frame(run_id), rejected_items)
        log.info("ETL %s | run_id=%s | %.2f detik", status, run_id, duration)

    return {"run_id": run_id, **counts}
