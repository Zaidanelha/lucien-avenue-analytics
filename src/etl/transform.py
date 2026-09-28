"""Tahap TRANSFORM: pembersihan data dan pembentukan star schema.

Semua fungsi di sini bersifat "pure" (input DataFrame -> output DataFrame, tanpa
akses database) supaya mudah diuji dengan unit test.
"""
from datetime import date

import numpy as np
import pandas as pd

from src.etl import reference as ref


# ---------------------------------------------------------------------------
# Standarisasi atribut
# ---------------------------------------------------------------------------
def normalize_email(emails: pd.Series) -> pd.Series:
    """' Budi@Gmail.com ' -> 'budi@gmail.com'."""
    return emails.astype("string").str.strip().str.lower()


def normalize_gender(values: pd.Series) -> pd.Series:
    """'L', 'Laki-laki', 'pria' -> 'Pria'; 'P', 'Perempuan' -> 'Wanita'; lainnya -> 'Tidak diketahui'."""
    cleaned = values.astype("string").str.strip().str.lower()
    return cleaned.map(ref.GENDER_MAP).fillna(ref.UNKNOWN).astype(str)


def _canonical_city(token) -> str:
    if token is None or pd.isna(token):
        return ref.UNKNOWN
    t = str(token).strip().lower()
    for prefix in ref.CITY_PREFIXES:
        if t.startswith(prefix):
            t = t[len(prefix):].strip()
    if t in ref.CITY_ALIASES:
        return ref.CITY_ALIASES[t]
    canonical = {c.lower(): c for c in ref.CITY_PROVINCE}
    return canonical.get(t, ref.OTHER)


def extract_city(alamat: pd.Series) -> pd.Series:
    """Mengambil kota dari alamat berformat 'jalan, kota, provinsi' lalu menstandarkannya."""
    parts = alamat.astype("string").str.split(",")
    city_token = parts.map(lambda p: p[-2] if isinstance(p, list) and len(p) >= 3 else None)
    return city_token.map(_canonical_city).astype(str)


def city_to_province(city: pd.Series) -> pd.Series:
    return city.map(ref.CITY_PROVINCE).fillna(ref.UNKNOWN).astype(str)


def normalize_brand(brand: pd.Series) -> pd.Series:
    cleaned = brand.astype("string").str.strip()
    return cleaned.str.lower().map(ref.BRAND_CANONICAL).fillna(cleaned.str.title()).fillna(ref.UNKNOWN).astype(str)


def clean_birth_date(birth: pd.Series, reference_date: date) -> pd.Series:
    """Tanggal lahir yang tidak masuk akal (umur < 10 atau > 90 tahun) dikosongkan."""
    birth = pd.to_datetime(birth, errors="coerce")
    age = (pd.Timestamp(reference_date) - birth).dt.days / 365.25
    return birth.where((age >= 10) & (age <= 90))


def age_group(birth: pd.Series, reference_date: date) -> pd.Series:
    age = (pd.Timestamp(reference_date) - pd.to_datetime(birth, errors="coerce")).dt.days / 365.25
    groups = pd.cut(age, bins=[0, 18, 25, 35, 45, 200], right=False,
                    labels=["< 18", "18-24", "25-34", "35-44", "45+"])
    return groups.astype(object).where(groups.notna(), ref.UNKNOWN).astype(str)


def is_internal_email(emails: pd.Series) -> pd.Series:
    domain = normalize_email(emails).str.split("@").str[-1]
    return domain.isin(ref.INTERNAL_EMAIL_DOMAINS).fillna(False).astype(bool)


# ---------------------------------------------------------------------------
# Dimensi
# ---------------------------------------------------------------------------
def build_dim_date(start: date, end: date) -> pd.DataFrame:
    """Dimensi tanggal lengkap (termasuk penanda gajian, Harbolnas, Ramadan)."""
    dates = pd.date_range(start, end, freq="D")
    df = pd.DataFrame({"full_date": dates.date})
    df["date_key"] = dates.year * 10000 + dates.month * 100 + dates.day
    df["year"] = dates.year
    df["quarter"] = dates.quarter
    df["month"] = dates.month
    df["month_name"] = [ref.MONTH_NAMES[m - 1] for m in dates.month]
    df["month_label"] = dates.strftime("%Y-%m")
    df["day"] = dates.day
    df["day_of_week"] = dates.dayofweek + 1  # 1 = Senin
    df["day_name"] = [ref.DAY_NAMES[d] for d in dates.dayofweek]
    df["is_weekend"] = (dates.dayofweek >= 5).astype(int)
    df["is_payday_period"] = ((dates.day >= 25) | (dates.day == 1)).astype(int)
    df["is_harbolnas"] = (((dates.month == 11) & (dates.day == 11)) |
                          ((dates.month == 12) & (dates.day == 12))).astype(int)
    df["is_twin_date"] = (dates.month == dates.day).astype(int)
    ramadan = np.zeros(len(dates), dtype=int)
    for r_start, r_end in ref.RAMADAN_PERIODS:
        ramadan |= ((dates >= pd.Timestamp(r_start)) & (dates <= pd.Timestamp(r_end))).astype(int)
    df["is_ramadan"] = ramadan
    # Angka urut hari & bulan: memudahkan hitung selisih waktu di SQL tanpa fungsi tanggal
    df["day_number"] = (dates - pd.Timestamp("2000-01-01")).days
    df["month_number"] = dates.year * 12 + dates.month
    return df[["date_key", "full_date", "year", "quarter", "month", "month_name", "month_label",
               "day", "day_of_week", "day_name", "is_weekend", "is_payday_period",
               "is_harbolnas", "is_twin_date", "is_ramadan", "day_number", "month_number"]]


def build_dim_customer(users: pd.DataFrame, reference_date: date) -> pd.DataFrame:
    """Dimensi pelanggan. Data pribadi (nama, email, telepon, alamat lengkap, password)
    sengaja TIDAK dimuat ke warehouse (prinsip minimisasi data pribadi)."""
    df = users.loc[~is_internal_email(users["email"])].copy()
    df["city"] = extract_city(df["alamat"])
    dim = pd.DataFrame({
        "user_id": df["user_id"].astype(int),
        "gender": normalize_gender(df["jenis_kelamin"]),
        "age_group": age_group(clean_birth_date(df["tanggal_lahir"], reference_date), reference_date),
        "city": df["city"],
        "province": city_to_province(df["city"]),
        "signup_date": pd.to_datetime(df["created_at"]).dt.date,
    }).sort_values("user_id").reset_index(drop=True)
    dim.insert(0, "customer_key", np.arange(1, len(dim) + 1))
    return dim


def build_dim_product(products: pd.DataFrame) -> pd.DataFrame:
    price = products["harga_retail"].astype(float)
    dim = pd.DataFrame({
        "produk_id": products["produk_id"].astype(int),
        "product_name": products["nama_sepatu"].astype(str),
        "model_name": products["nama_sepatu"].astype(str).str.split(" '").str[0],
        "brand": normalize_brand(products["brand"]),
        "category": products["jenis"].astype("string").fillna(ref.OTHER).astype(str),
        "gender_segment": products["gender"].astype("string").fillna(ref.UNKNOWN).astype(str),
        "material": products["material"].astype("string").fillna(ref.UNKNOWN).astype(str),
        "retail_price": price,
        "price_tier": pd.cut(price, bins=[0, 1_500_000, 2_500_000, 5_000_000, np.inf], right=False,
                             labels=["Entry (<1,5 jt)", "Mid (1,5-2,5 jt)", "Premium (2,5-5 jt)",
                                     "Hype/Collab (>5 jt)"]).astype(str),
        "release_date": pd.to_datetime(products["tanggal_rilis"], errors="coerce").dt.date,
    }).sort_values("produk_id").reset_index(drop=True)
    dim.insert(0, "product_key", np.arange(1, len(dim) + 1))
    return dim


# ---------------------------------------------------------------------------
# Pembersihan transaksi
# ---------------------------------------------------------------------------
def find_duplicate_orders(orders: pd.DataFrame, items: pd.DataFrame, window_seconds: int = 60) -> pd.Series:
    """Mendeteksi pesanan ganda: user sama, daftar produk sama, total sama, dibuat
    dalam selang <= window_seconds dari pesanan sebelumnya. Mengembalikan pesanan_id duplikat.

    Catatan: signature sengaja hanya memakai produk_id (tanpa quantity), karena kolom
    quantity sendiri bisa rusak. Versi awal yang memakai quantity meloloskan 2 duplikat.
    """
    signature = (items.sort_values(["pesanan_id", "produk_id"])
                 .assign(token=lambda d: d["produk_id"].astype(str))
                 .groupby("pesanan_id")["token"].agg("|".join).rename("signature"))
    o = orders[["pesanan_id", "user_id", "jumlah_total", "created_at"]].merge(
        signature, left_on="pesanan_id", right_index=True, how="left")
    o = o.sort_values(["user_id", "signature", "jumlah_total", "created_at"])
    keys = ["user_id", "signature", "jumlah_total"]
    same_as_prev = (o[keys] == o[keys].shift()).all(axis=1)
    gap_seconds = o["created_at"].diff().dt.total_seconds()
    is_dup = same_as_prev & (gap_seconds <= window_seconds)
    return o.loc[is_dup, "pesanan_id"]


def split_valid_items(items: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Item dengan quantity <= 0 atau harga <= 0 dipisahkan (dikarantina)."""
    valid_mask = (items["quantity"] > 0) & (items["harga"] > 0)
    return items[valid_mask].copy(), items[~valid_mask].copy()


def find_total_mismatch(orders: pd.DataFrame, tolerance: float = 1.0) -> pd.Series:
    """Pesanan yang jumlah_total-nya tidak sama dengan subtotal - discount."""
    expected = orders["subtotal"] - orders["discount"]
    return orders.loc[(orders["jumlah_total"] - expected).abs() > tolerance, "pesanan_id"]


def allocate_discount(items: pd.DataFrame, orders: pd.DataFrame) -> pd.DataFrame:
    """Diskon level pesanan dibagi ke setiap item secara proporsional terhadap nilainya.
    Nilai dihitung ulang dari item, sehingga tidak bergantung pada jumlah_total yang bisa salah."""
    df = items.merge(orders[["pesanan_id", "subtotal", "discount"]], on="pesanan_id", how="inner")
    df["gross_amount"] = df["harga"] * df["quantity"]
    rate = np.where(df["subtotal"] > 0, df["discount"] / df["subtotal"], 0.0)
    df["discount_amount"] = (df["gross_amount"] * rate).round(2)
    df["net_amount"] = df["gross_amount"] - df["discount_amount"]
    return df.drop(columns=["subtotal", "discount"])


def build_fact_sales(orders: pd.DataFrame, items: pd.DataFrame, payments: pd.DataFrame,
                     shipments: pd.DataFrame, returns: pd.DataFrame,
                     dim_customer: pd.DataFrame, dim_product: pd.DataFrame) -> pd.DataFrame:
    """Tabel fakta penjualan dengan grain: satu baris per item pesanan."""
    lines = allocate_discount(items, orders)
    lines = lines.merge(orders[["pesanan_id", "user_id", "created_at", "status_pesanan", "promotion_code"]],
                        on="pesanan_id", how="inner")
    lines = lines.merge(dim_customer[["user_id", "customer_key"]], on="user_id", how="inner")
    lines = lines.merge(dim_product[["produk_id", "product_key"]], on="produk_id", how="inner")

    pay = payments.sort_values("pembayaran_id").drop_duplicates("pesanan_id", keep="last")
    ship = shipments.sort_values("pengiriman_id").drop_duplicates("pesanan_id", keep="last")
    ret = returns.sort_values("pengembalian_id").drop_duplicates("pesanan_id", keep="last")
    lines = (lines
             .merge(pay[["pesanan_id", "metode_pembayaran"]], on="pesanan_id", how="left")
             .merge(ship[["pesanan_id", "metode_pengiriman"]], on="pesanan_id", how="left")
             .merge(ret[["pesanan_id", "pengembalian"]], on="pesanan_id", how="left"))

    created = pd.to_datetime(lines["created_at"])
    fact = pd.DataFrame({
        "order_item_id": lines["barang_pesanan_id"].astype(int),
        "order_id": lines["pesanan_id"].astype(int),
        "date_key": (created.dt.year * 10000 + created.dt.month * 100 + created.dt.day).astype(int),
        "order_hour": created.dt.hour.astype(int),
        "customer_key": lines["customer_key"].astype(int),
        "product_key": lines["product_key"].astype(int),
        "quantity": lines["quantity"].astype(int),
        "unit_price": lines["harga"].astype(float),
        "gross_amount": lines["gross_amount"].astype(float),
        "discount_amount": lines["discount_amount"].astype(float),
        "net_amount": lines["net_amount"].astype(float),
        "promotion_code": lines["promotion_code"].astype("string").fillna("-").astype(str),
        "order_status": lines["status_pesanan"].astype(str),
        "payment_method": lines["metode_pembayaran"].astype("string").fillna(ref.UNKNOWN).astype(str),
        "courier": lines["metode_pengiriman"].astype("string").fillna("-").astype(str),
        "is_returned": (lines["status_pesanan"] == "dikembalikan").astype(int),
        "return_reason": lines["pengembalian"].astype("string").fillna("-").astype(str),
    })
    return fact.sort_values("order_item_id").reset_index(drop=True)
