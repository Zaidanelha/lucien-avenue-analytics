"""Unit test untuk fungsi-fungsi transformasi ETL.  Jalankan: pytest -v"""
from datetime import date

import pandas as pd
import pytest

from src.etl import transform as tf
from src.etl.quality import DataQualityError, assert_integrity


def test_normalize_email_trims_and_lowercases():
    result = tf.normalize_email(pd.Series([" Budi.Santoso@Gmail.com ", "ani@yahoo.com"]))
    assert result.tolist() == ["budi.santoso@gmail.com", "ani@yahoo.com"]


@pytest.mark.parametrize("raw, expected", [
    ("L", "Pria"), ("Laki-laki", "Pria"), ("pria", "Pria"),
    ("P", "Wanita"), ("Perempuan", "Wanita"), (" wanita ", "Wanita"),
    (None, "Tidak diketahui"), ("x", "Tidak diketahui"),
])
def test_normalize_gender(raw, expected):
    assert tf.normalize_gender(pd.Series([raw])).iloc[0] == expected


@pytest.mark.parametrize("alamat, expected", [
    ("Jl. Malioboro No. 1, Jogja, DI Yogyakarta", "Yogyakarta"),
    ("Jl. Kaliurang No. 5, Kota Yogyakarta, DI Yogyakarta", "Yogyakarta"),
    ("Jl. Sudirman No. 2, Jaksel, DKI Jakarta", "Jakarta Selatan"),
    ("Jl. Slamet Riyadi No. 3, SOLO, Jawa Tengah", "Surakarta"),
    ("Jl. Magelang No. 9, Kab. Sleman, DI Yogyakarta", "Sleman"),
    ("Jl. Braga No. 7, bandung , Jawa Barat", "Bandung"),
    ("Jl. Antah Berantah No. 1, Atlantis, Negeri Dongeng", "Lainnya"),
    (None, "Tidak diketahui"),
])
def test_extract_city_standardizes_variants(alamat, expected):
    assert tf.extract_city(pd.Series([alamat])).iloc[0] == expected


def test_clean_birth_date_removes_impossible_values():
    ref = date(2025, 12, 31)
    birth = pd.Series(["1900-01-01", "2031-05-05", "1998-04-12", None])
    cleaned = tf.clean_birth_date(birth, ref)
    assert cleaned.isna().tolist() == [True, True, False, True]


def test_age_group_buckets():
    ref = date(2025, 12, 31)
    groups = tf.age_group(pd.Series(["2010-01-01", "2003-01-01", "1995-01-01", "1970-01-01", None]), ref)
    assert groups.tolist() == ["< 18", "18-24", "25-34", "45+", "Tidak diketahui"]


def test_internal_accounts_detected():
    emails = pd.Series(["admin@lucien.com", " QA@TEST.COM ", "budi@gmail.com"])
    assert tf.is_internal_email(emails).tolist() == [True, True, False]


def _orders_items():
    orders = pd.DataFrame({
        "pesanan_id": [1, 2, 3, 4],
        "user_id": [10, 10, 10, 20],
        "jumlah_total": [1_000_000.0, 1_000_000.0, 1_000_000.0, 1_000_000.0],
        "created_at": pd.to_datetime(["2025-01-01 10:00:00", "2025-01-01 10:00:15",  # duplikat (15 detik)
                                      "2025-01-02 10:00:00",                         # beli lagi besoknya
                                      "2025-01-01 10:00:05"]),                       # user lain
    })
    items = pd.DataFrame({
        "pesanan_id": [1, 2, 3, 4],
        "produk_id": [7, 7, 7, 7],
        "quantity": [1, -1, 1, 1],  # quantity pesanan #2 rusak, tetap harus terdeteksi duplikat
        "harga": [1_000_000.0] * 4,
    })
    return orders, items


def test_find_duplicate_orders_only_flags_double_submit():
    orders, items = _orders_items()
    assert tf.find_duplicate_orders(orders, items).tolist() == [2]


def test_split_valid_items_quarantines_bad_quantity():
    _, items = _orders_items()
    valid, rejected = tf.split_valid_items(items)
    assert rejected["pesanan_id"].tolist() == [2]
    assert len(valid) == 3


def test_allocate_discount_sums_to_order_discount():
    orders = pd.DataFrame({"pesanan_id": [1], "subtotal": [3_000_000.0], "discount": [300_000.0]})
    items = pd.DataFrame({"pesanan_id": [1, 1], "produk_id": [1, 2],
                          "harga": [1_000_000.0, 1_000_000.0], "quantity": [1, 2]})
    lines = tf.allocate_discount(items, orders)
    assert lines["discount_amount"].sum() == pytest.approx(300_000.0)
    assert lines["discount_amount"].tolist() == pytest.approx([100_000.0, 200_000.0])
    assert lines["net_amount"].sum() == pytest.approx(2_700_000.0)


def test_find_total_mismatch():
    orders = pd.DataFrame({"pesanan_id": [1, 2], "subtotal": [100.0, 100.0],
                           "discount": [10.0, 10.0], "jumlah_total": [90.0, 100.0]})
    assert tf.find_total_mismatch(orders).tolist() == [2]


def test_dim_date_flags():
    dim = tf.build_dim_date(date(2024, 11, 10), date(2024, 11, 12)).set_index("date_key")
    assert list(dim.index) == [20241110, 20241111, 20241112]
    assert dim.loc[20241111, "is_harbolnas"] == 1
    assert dim.loc[20241111, "is_twin_date"] == 1
    assert dim.loc[20241110, "day_name"] == "Minggu"
    assert dim.loc[20241110, "is_weekend"] == 1
    assert dim.loc[20241112, "month_number"] == 2024 * 12 + 11


def test_integrity_check_blocks_orphan_keys():
    dim_date = pd.DataFrame({"date_key": [20250101]})
    dim_customer = pd.DataFrame({"customer_key": [1]})
    dim_product = pd.DataFrame({"product_key": [1]})
    fact = pd.DataFrame({"order_item_id": [1], "date_key": [20250101], "customer_key": [99],
                         "product_key": [1], "net_amount": [100.0]})
    with pytest.raises(DataQualityError, match="customer_key"):
        assert_integrity(dim_date, dim_customer, dim_product, fact)
