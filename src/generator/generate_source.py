"""Generator data sintetis untuk database sumber (OLTP) Lucien Avenue.

Data dibuat dengan pola yang mendekati perilaku e-commerce sungguhan di Indonesia:
- tren pertumbuhan penjualan dari waktu ke waktu,
- lonjakan saat Harbolnas (11.11, 12.12), tanggal kembar, gajian, dan Ramadan,
- sebagian kecil pelanggan loyal menyumbang porsi besar transaksi (distribusi lognormal),
- produk populer vs produk niche (katalog berbobot).

Selain itu, beberapa masalah kualitas data SENGAJA disisipkan (duplikat pesanan,
format kota/gender tidak konsisten, quantity tidak valid, total tidak cocok, akun
testing) agar pipeline ETL harus membersihkannya seperti di dunia nyata.
"""
import logging
from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd
from faker import Faker

import config
from src.db import get_engine, run_sql_file, write_df
from src.generator import catalog

log = logging.getLogger(__name__)

WEEKDAY_FACTOR = [0.90, 0.90, 0.95, 0.95, 1.05, 1.20, 1.15]  # Senin..Minggu
HOUR_WEIGHTS = np.array([1, 0.5, 0.3, 0.2, 0.2, 0.4, 1, 2, 3, 4, 4, 5,
                         7, 6, 5, 4, 4, 4, 5, 7, 8, 8, 6, 3], dtype=float)
HOUR_WEIGHTS /= HOUR_WEIGHTS.sum()


# ---------------------------------------------------------------------------
# Pola musiman
# ---------------------------------------------------------------------------
def ramadan_status(d: date) -> tuple[bool, bool]:
    """Mengembalikan (sedang_ramadan, 10_hari_menjelang_lebaran)."""
    for start, end, eid in catalog.RAMADAN_PERIODS:
        if start <= d <= end:
            return True, (eid - d).days <= 10
    return False, False


def day_multiplier(d: date, t: float) -> float:
    """Pengali volume pesanan harian. t = posisi hari dalam rentang data (0..1)."""
    m = (1.0 + 0.5 * t) * WEEKDAY_FACTOR[d.weekday()]
    if d.day >= 25 or d.day == 1:  # periode gajian
        m *= 1.25
    in_ramadan, pre_lebaran = ramadan_status(d)
    if in_ramadan:
        m *= 1.3 * (1.4 if pre_lebaran else 1.0)
    if (d.month, d.day) == (11, 11):
        m *= 3.5
    elif (d.month, d.day) == (12, 12):
        m *= 3.0
    elif d.month == d.day and d.month in (9, 10):  # 9.9 dan 10.10
        m *= 1.8
    if d.month == 12:
        m *= 1.1
    return m


def pick_promo(d: date, rng: np.random.Generator) -> tuple[str | None, float]:
    """Menentukan kode promo (jika ada) dan persentase diskonnya."""
    in_ramadan, _ = ramadan_status(d)
    if (d.month, d.day) == (11, 11) and rng.random() < 0.7:
        return "HARBOLNAS11", 0.11
    if (d.month, d.day) == (12, 12) and rng.random() < 0.7:
        return "HARBOLNAS12", 0.12
    if in_ramadan and rng.random() < 0.35:
        return "RAMADAN10", 0.10
    if (d.day >= 25 or d.day == 1) and rng.random() < 0.25:
        return "GAJIAN5", 0.05
    if rng.random() < 0.05:
        return "LUCIEN5", 0.05
    return None, 0.0


# ---------------------------------------------------------------------------
# Master data: produk & pelanggan
# ---------------------------------------------------------------------------
def build_products(rng: np.random.Generator, start: date, end: date) -> pd.DataFrame:
    rows, pid = [], 1
    period_days = (end - start).days
    for name, brand, jenis, material, price, popularity, colorways in catalog.MODELS:
        variants = [("adult", 1.0)] + ([("kids", 0.6)] if name in catalog.KIDS_MODELS else [])
        for variant, price_factor in variants:
            for color in colorways:
                is_kids = variant == "kids"
                # 25% produk dirilis di tengah periode data (produk baru)
                if popularity >= 3 and rng.random() < 0.25:
                    release = start + timedelta(days=int(rng.integers(30, period_days - 60)))
                else:
                    release = date(2019, 1, 1) + timedelta(days=int(rng.integers(0, 1800)))
                harga = round(price * price_factor * rng.uniform(0.95, 1.05) / 10_000) * 10_000
                gender = "Anak" if is_kids else rng.choice(["Unisex", "Pria", "Wanita"], p=[0.7, 0.15, 0.15])
                rows.append({
                    "produk_id": pid,
                    "nama_sepatu": f"{name}{' (GS)' if is_kids else ''} '{color}'",
                    "brand": brand,
                    "jenis": jenis,
                    "material": material,
                    "ukuran": "28-35" if is_kids else "36-45",
                    "warna": color,
                    "gender": gender,
                    "tanggal_rilis": release,
                    "sku": f"{brand[:3].upper()}-{pid:04d}",
                    "harga_retail": float(harga),
                    "stok": int(rng.integers(0, 60)),
                    "created_at": datetime.combine(min(release, start), datetime.min.time()),
                    "updated_at": datetime.combine(min(release, start), datetime.min.time()),
                    "_weight": popularity * rng.lognormal(0, 0.3) * (0.6 if is_kids else 1.0),
                })
                pid += 1
    df = pd.DataFrame(rows)
    # Masalah kualitas data: brand huruf kecil & jenis kosong di beberapa produk
    messy = rng.choice(df.index, size=4, replace=False)
    df.loc[messy[:2], "brand"] = df.loc[messy[:2], "brand"].str.lower()
    df.loc[messy[2:], "jenis"] = None
    return df


def _messy_gender(gender: str, rng: np.random.Generator) -> str | None:
    if gender == "Pria":
        options = ["Pria", "L", "Laki-laki", "pria", None]
    else:
        options = ["Wanita", "P", "Perempuan", "wanita", None]
    return options[rng.choice(5, p=[0.70, 0.10, 0.10, 0.05, 0.05])]


def build_users(fake: Faker, rng: np.random.Generator, n: int, start: date, end: date) -> pd.DataFrame:
    city_weights = np.array([c[2] for c in catalog.CITIES], dtype=float)
    city_weights /= city_weights.sum()
    period_days = (end - start).days
    domains = ["gmail.com", "yahoo.com", "outlook.com", "icloud.com"]

    rows = []
    for uid in range(1, n + 1):
        gender = "Pria" if rng.random() < 0.62 else "Wanita"
        first = fake.first_name_male() if gender == "Pria" else fake.first_name_female()
        last = fake.last_name() if rng.random() > 0.10 else None

        # 35% pelanggan sudah terdaftar sebelum periode data, sisanya bertambah seiring waktu
        if rng.random() < 0.35:
            signup = start - timedelta(days=int(rng.integers(1, 730)))
        else:
            signup = start + timedelta(days=int(period_days * np.sqrt(rng.random())))
        signup_dt = datetime.combine(signup, datetime.min.time()) + timedelta(minutes=int(rng.integers(0, 1440)))

        # Tanggal lahir: mayoritas 17-40 tahun, sebagian kosong, sedikit yang tidak valid
        birth = None
        roll = rng.random()
        if roll < 0.002:
            birth = [date(1900, 1, 1), date(2031, 5, 5)][rng.integers(2)]
        elif roll > 0.10:
            age = float(np.clip(rng.normal(27, 6), 15, 60))
            birth = start - timedelta(days=int(age * 365.25))

        city, province, _, variants = catalog.CITIES[rng.choice(len(catalog.CITIES), p=city_weights)]
        city_text = city if rng.random() < 0.8 else variants[rng.integers(len(variants))]
        alamat = None if rng.random() < 0.05 else f"{fake.street_name()} No. {rng.integers(1, 200)}, {city_text}, {province}"

        email = f"{first}.{last or 'user'}{uid}@{rng.choice(domains, p=[0.7, 0.15, 0.1, 0.05])}".lower().replace(" ", "")
        if rng.random() < 0.03:  # masalah kualitas data: kapitalisasi & spasi
            email = f" {email.capitalize()} "

        rows.append({
            "user_id": uid,
            "first_name": first,
            "last_name": last,
            "tanggal_lahir": birth,
            "alamat": alamat,
            "email": email,
            "password": "$2y$12$" + fake.sha256()[:53],
            "no_telepon": fake.phone_number(),
            "jenis_kelamin": _messy_gender(gender, rng),
            "created_at": signup_dt,
            "updated_at": signup_dt,
            "_weight": rng.lognormal(0, 1.0),  # tingkat aktivitas belanja (disembunyikan)
        })

    # Akun internal/testing yang ikut tersimpan di database produksi
    test_accounts = ["admin@lucien.com", "test@lucien.com", "qa.tester@test.com", "dummy1@test.com"]
    for i, email in enumerate(test_accounts, start=n + 1):
        created = datetime.combine(start - timedelta(days=200), datetime.min.time())
        rows.append({
            "user_id": i, "first_name": "Test", "last_name": f"Account {i - n}", "tanggal_lahir": None,
            "alamat": "Jl. Testing No. 1, Yogyakarta, DI Yogyakarta", "email": email,
            "password": "$2y$12$" + fake.sha256()[:53], "no_telepon": None, "jenis_kelamin": None,
            "created_at": created, "updated_at": created, "_weight": 0.0,
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Transaksi
# ---------------------------------------------------------------------------
def build_transactions(users: pd.DataFrame, products: pd.DataFrame, rng: np.random.Generator,
                       start: date, end: date, base_daily: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Membangkitkan pesanan & item pesanan hari demi hari."""
    real_users = users[users["_weight"] > 0].sort_values("created_at").reset_index(drop=True)
    # tanggal disimpan sebagai angka ordinal agar perbandingan cepat di numpy
    signup_ord = np.array([ts.date().toordinal() for ts in real_users["created_at"]])
    user_ids = real_users["user_id"].to_numpy()
    user_w = real_users["_weight"].to_numpy()
    test_ids = users.loc[users["_weight"] == 0, "user_id"].to_numpy()

    prod_ids = products["produk_id"].to_numpy()
    prod_price = products["harga_retail"].to_numpy()
    release_ord = np.array([d.toordinal() for d in products["tanggal_rilis"]])
    prod_w = products["_weight"].to_numpy()

    total_days = (end - start).days
    orders, items = [], []
    okey = 0
    for day_idx in range(total_days + 1):
        d = start + timedelta(days=day_idx)
        n_orders = rng.poisson(base_daily * day_multiplier(d, day_idx / total_days))

        eligible_u = int(np.searchsorted(signup_ord, d.toordinal(), side="right"))
        if eligible_u == 0 or n_orders == 0:
            continue
        uw = user_w[:eligible_u] / user_w[:eligible_u].sum()
        buyers = rng.choice(user_ids[:eligible_u], size=n_orders, p=uw)
        # sesekali akun testing membuat pesanan percobaan
        if rng.random() < 0.04:
            buyers = np.append(buyers, rng.choice(test_ids))

        pw = prod_w * (release_ord <= d.toordinal())
        pw = pw / pw.sum()
        days_to_end = (end - d).days

        for buyer in buyers:
            okey += 1
            ts = datetime.combine(d, datetime.min.time()) + timedelta(
                hours=int(rng.choice(24, p=HOUR_WEIGHTS)), minutes=int(rng.integers(0, 60)),
                seconds=int(rng.integers(0, 60)))
            n_items = int(rng.choice([1, 2, 3], p=[0.80, 0.16, 0.04]))
            chosen = rng.choice(len(prod_ids), size=n_items, replace=False, p=pw)

            subtotal = 0.0
            for idx in chosen:
                qty = 1 if rng.random() < 0.95 else 2
                subtotal += prod_price[idx] * qty
                items.append({"okey": okey, "produk_id": int(prod_ids[idx]),
                              "harga": float(prod_price[idx]), "quantity": qty})

            promo, pct = pick_promo(d, rng)
            discount = round(subtotal * pct, -2)

            if days_to_end < 3:
                status = rng.choice(["diproses", "dikirim"])
            elif days_to_end < 7:
                status = "dikirim" if rng.random() < 0.4 else "selesai"
            else:
                status = "dibatalkan" if rng.random() < 0.08 else "selesai"

            orders.append({"okey": okey, "user_id": int(buyer), "subtotal": subtotal,
                           "discount": discount, "jumlah_total": subtotal - discount,
                           "promotion_code": promo, "status_pesanan": status,
                           "created_at": ts, "updated_at": ts + timedelta(minutes=int(rng.integers(5, 120))),
                           "_is_duplicate": False})
    return pd.DataFrame(orders), pd.DataFrame(items)


def apply_returns(orders: pd.DataFrame, items: pd.DataFrame, products: pd.DataFrame,
                  rng: np.random.Generator, end: date) -> pd.DataFrame:
    """Menandai sebagian pesanan selesai sebagai dikembalikan (retur)."""
    jenis = items.merge(products[["produk_id", "jenis", "gender"]], on="produk_id")
    has_running = set(jenis.loc[jenis["jenis"] == "Lari", "okey"])
    has_kids = set(jenis.loc[jenis["gender"] == "Anak", "okey"])

    orders["_return_reason"] = None
    orders["_return_at"] = pd.NaT
    cutoff = pd.Timestamp(end - timedelta(days=14))
    candidates = orders.index[(orders["status_pesanan"] == "selesai") & (orders["created_at"] < cutoff)]
    for i in candidates:
        key = orders.at[i, "okey"]
        p = 0.03 * (1.6 if key in has_running else 1.0) * (1.3 if key in has_kids else 1.0)
        if rng.random() < p:
            orders.at[i, "status_pesanan"] = "dikembalikan"
            orders.at[i, "_return_reason"] = rng.choice(catalog.RETURN_REASONS, p=[0.55, 0.15, 0.15, 0.15])
            returned_at = orders.at[i, "created_at"] + timedelta(days=int(rng.integers(5, 14)))
            orders.at[i, "_return_at"] = returned_at
            orders.at[i, "updated_at"] = returned_at
    return orders


def inject_duplicates(orders: pd.DataFrame, items: pd.DataFrame,
                      rng: np.random.Generator) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Masalah kualitas data: pesanan tersubmit dua kali (double-click checkout)."""
    dup_idx = rng.choice(orders.index, size=int(len(orders) * 0.004), replace=False)
    dups = orders.loc[dup_idx].copy()
    next_key = orders["okey"].max() + 1
    key_map = {old: next_key + i for i, old in enumerate(dups["okey"])}
    dups["created_at"] = dups["created_at"] + pd.to_timedelta(rng.integers(2, 20, size=len(dups)), unit="s")
    dups["okey"] = dups["okey"].map(key_map)
    dups["_is_duplicate"] = True
    dups["_return_reason"] = None
    dups["_return_at"] = pd.NaT
    dup_items = items[items["okey"].isin(list(key_map))].copy()
    dup_items["okey"] = dup_items["okey"].map(key_map)
    return pd.concat([orders, dups], ignore_index=True), pd.concat([items, dup_items], ignore_index=True)


def payment_weights(t: float) -> np.ndarray:
    """Pergeseran preferensi pembayaran: e-wallet & QRIS makin populer."""
    early = np.array([0.35, 0.20, 0.15, 0.10, 0.20])
    late = np.array([0.25, 0.20, 0.20, 0.22, 0.13])
    w = early + (late - early) * t
    return w / w.sum()


def build_fulfilment(orders: pd.DataFrame, rng: np.random.Generator, start: date, end: date):
    """Membuat tabel payments, shipments, dan returns dari pesanan (bukan duplikat)."""
    total_days = (end - start).days
    payments, shipments, returns = [], [], []
    prefixes = {"JNE": "JNE", "J&T Express": "JT", "SiCepat": "SCP", "AnterAja": "AA"}
    for o in orders[~orders["_is_duplicate"]].to_dict("records"):
        t = (o["created_at"].date() - start).days / total_days
        cancelled = o["status_pesanan"] == "dibatalkan"
        payments.append({
            "pembayaran_id": len(payments) + 1, "pesanan_id": o["pesanan_id"],
            "metode_pembayaran": catalog.PAYMENT_METHODS[rng.choice(5, p=payment_weights(t))],
            "status_pembayaran": (rng.choice(["expire", "cancel"], p=[0.7, 0.3]) if cancelled else "settlement"),
            "jumlah": o["jumlah_total"],
        })
        if cancelled:
            continue
        courier = catalog.COURIERS[rng.choice(4, p=[0.35, 0.30, 0.25, 0.10])]
        ship_status = {"selesai": "terkirim", "dikembalikan": "terkirim",
                       "dikirim": "dalam perjalanan", "diproses": "dikemas"}[o["status_pesanan"]]
        shipments.append({
            "pengiriman_id": len(shipments) + 1, "pesanan_id": o["pesanan_id"],
            "track_nomor": None if o["status_pesanan"] == "diproses" else f"{prefixes[courier]}{rng.integers(10**9, 10**10)}",
            "metode_pengiriman": courier, "status_pengiriman": ship_status,
            "perkiraan_pengiriman": o["created_at"].date() + timedelta(days=int(rng.integers(2, 6))),
        })
        if o["status_pesanan"] == "dikembalikan":
            returns.append({
                "pengembalian_id": len(returns) + 1, "pesanan_id": o["pesanan_id"],
                "pembelian": f"Pesanan #{o['pesanan_id']}", "pengembalian": o["_return_reason"],
                "created_at": o["_return_at"], "updated_at": o["_return_at"],
            })
    return pd.DataFrame(payments), pd.DataFrame(shipments), pd.DataFrame(returns)


# ---------------------------------------------------------------------------
# Orkestrasi
# ---------------------------------------------------------------------------
def generate() -> dict:
    """Membangkitkan seluruh data sumber dan menuliskannya ke SOURCE_DB_URL."""
    rng = np.random.default_rng(config.RANDOM_SEED)
    fake = Faker("id_ID")
    Faker.seed(config.RANDOM_SEED)
    start = date.fromisoformat(config.START_DATE)
    end = date.fromisoformat(config.END_DATE)

    log.info("Membuat katalog produk & pelanggan...")
    products = build_products(rng, start, end)
    users = build_users(fake, rng, config.N_CUSTOMERS, start, end)

    log.info("Membangkitkan transaksi %s s.d. %s...", start, end)
    orders, items = build_transactions(users, products, rng, start, end, config.BASE_DAILY_ORDERS)
    orders = apply_returns(orders, items, products, rng, end)
    orders, items = inject_duplicates(orders, items, rng)

    # Urutkan berdasarkan waktu lalu berikan ID final (seperti auto-increment)
    orders = orders.sort_values("created_at").reset_index(drop=True)
    orders["pesanan_id"] = np.arange(1, len(orders) + 1)
    items = items.merge(orders[["okey", "pesanan_id"]], on="okey").sort_values(["pesanan_id"]).reset_index(drop=True)
    items["barang_pesanan_id"] = np.arange(1, len(items) + 1)

    payments, shipments, returns = build_fulfilment(orders, rng, start, end)

    # Masalah kualitas data: total pesanan tidak cocok & quantity tidak valid
    bad_total = rng.choice(orders.index, size=int(len(orders) * 0.003), replace=False)
    orders.loc[bad_total, "jumlah_total"] += rng.choice([-50_000, 25_000, 100_000], size=len(bad_total))
    bad_qty = rng.choice(items.index, size=int(len(items) * 0.002), replace=False)
    items.loc[bad_qty, "quantity"] = rng.choice([0, -1], size=len(bad_qty))

    engine = get_engine(config.SOURCE_DB_URL)
    run_sql_file(engine, config.SQL_DIR / "source_schema.sql")
    counts = {
        "users": write_df(users.drop(columns="_weight"), "users", engine),
        "products": write_df(products.drop(columns="_weight"), "products", engine),
        "orders": write_df(orders[["pesanan_id", "user_id", "jumlah_total", "subtotal", "discount",
                                   "promotion_code", "status_pesanan", "created_at", "updated_at"]], "orders", engine),
        "order_items": write_df(items[["barang_pesanan_id", "pesanan_id", "produk_id", "harga", "quantity"]],
                                "order_items", engine),
        "payments": write_df(payments, "payments", engine),
        "shipments": write_df(shipments, "shipments", engine),
        "returns": write_df(returns, "returns", engine),
    }
    for table, n in counts.items():
        log.info("  %-12s %8s baris", table, f"{n:,}")
    return counts
