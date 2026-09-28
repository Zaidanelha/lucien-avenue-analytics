"""Dashboard Lucien Avenue Sales Analytics.

Jalankan dari folder root proyek:
    streamlit run dashboard/app.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import inspect, text

import config
from src.db import get_engine, read_sql_file

st.set_page_config(page_title="Lucien Avenue Sales Analytics", page_icon="👟", layout="wide")

REVENUE_STATUS = "selesai"
DAY_ORDER = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]


# ---------------------------------------------------------------------------
# Data access (di-cache agar dashboard responsif)
# ---------------------------------------------------------------------------
@st.cache_resource
def engine():
    return get_engine(config.WAREHOUSE_DB_URL)


@st.cache_data(ttl=600)
def load_sales() -> pd.DataFrame:
    query = """
        SELECT f.order_id, f.order_item_id, f.order_hour, f.quantity, f.gross_amount, f.discount_amount,
               f.net_amount, f.promotion_code, f.order_status, f.payment_method, f.courier,
               f.is_returned, f.return_reason,
               d.full_date, d.year, d.month_label, d.day_name,
               p.product_name, p.model_name, p.brand, p.category, p.price_tier,
               c.customer_key, c.gender, c.age_group, c.city, c.province
        FROM fact_sales f
        JOIN dim_date d     ON d.date_key = f.date_key
        JOIN dim_product p  ON p.product_key = f.product_key
        JOIN dim_customer c ON c.customer_key = f.customer_key
    """
    with engine().connect() as conn:
        df = pd.read_sql(text(query), conn)
    df["full_date"] = pd.to_datetime(df["full_date"])
    return df


@st.cache_data(ttl=600)
def load_sql(name: str) -> pd.DataFrame:
    return read_sql_file(engine(), config.SQL_DIR / "analytics" / f"{name}.sql")


@st.cache_data(ttl=600)
def load_table(query: str, params: dict | None = None) -> pd.DataFrame:
    """Query dengan parameter binding (bukan string formatting) untuk mencegah SQL injection."""
    with engine().connect() as conn:
        return pd.read_sql(text(query), conn, params=params or {})


def rupiah(value: float) -> str:
    """Format ringkas: Rp 76,7 M (miliar) / Rp 2,4 jt (juta)."""
    if abs(value) >= 1e9:
        return f"Rp {value / 1e9:,.1f} M".replace(",", "X").replace(".", ",").replace("X", ".")
    if abs(value) >= 1e6:
        return f"Rp {value / 1e6:,.1f} jt".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"Rp {value:,.0f}".replace(",", ".")


# ---------------------------------------------------------------------------
# Guard: warehouse harus sudah dibuat
# ---------------------------------------------------------------------------
if "fact_sales" not in inspect(engine()).get_table_names():
    st.error("Data warehouse belum tersedia. Jalankan dulu: `python run_pipeline.py all`")
    st.stop()

sales = load_sales()

# ---------------------------------------------------------------------------
# Sidebar filter
# ---------------------------------------------------------------------------
st.sidebar.title("👟 Lucien Avenue")
st.sidebar.caption("Sales Analytics Dashboard")
years = sorted(sales["year"].unique())
sel_years = st.sidebar.multiselect("Tahun", years, default=years)
sel_brands = st.sidebar.multiselect("Brand", sorted(sales["brand"].unique()))
sel_categories = st.sidebar.multiselect("Kategori", sorted(sales["category"].unique()))
sel_provinces = st.sidebar.multiselect("Provinsi", sorted(sales["province"].unique()))
st.sidebar.divider()
st.sidebar.info("Data bersifat **sintetis** (dibangkitkan dengan Python), meniru skema database "
                "aplikasi e-commerce Lucien Avenue. Pendapatan = pesanan berstatus *selesai*.")

mask = sales["year"].isin(sel_years or years)
if sel_brands:
    mask &= sales["brand"].isin(sel_brands)
if sel_categories:
    mask &= sales["category"].isin(sel_categories)
if sel_provinces:
    mask &= sales["province"].isin(sel_provinces)
data = sales[mask]
done = data[data["order_status"] == REVENUE_STATUS]
delivered = data[data["order_status"].isin(["selesai", "dikembalikan"])]

st.title("Lucien Avenue — Sales Analytics")
st.caption(f"Periode data: {sales['full_date'].min():%d %b %Y} – {sales['full_date'].max():%d %b %Y} · "
           f"{len(data):,} baris item pesanan sesuai filter")

tab_sales, tab_product, tab_customer, tab_dq = st.tabs(
    ["📈 Penjualan", "👟 Produk", "👥 Pelanggan", "🧪 Data Quality"])

# ---------------------------------------------------------------------------
# Tab Penjualan
# ---------------------------------------------------------------------------
with tab_sales:
    orders = done["order_id"].nunique()
    revenue = done["net_amount"].sum()
    return_rate = delivered.groupby("order_id")["is_returned"].max().mean() * 100 if len(delivered) else 0
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Pendapatan", rupiah(revenue))
    k2.metric("Pesanan selesai", f"{orders:,}".replace(",", "."))
    k3.metric("Rata-rata nilai pesanan", rupiah(revenue / orders if orders else 0))
    k4.metric("Pelanggan aktif", f"{done['customer_key'].nunique():,}".replace(",", "."))
    k5.metric("Tingkat retur", f"{return_rate:.2f}%")

    monthly = done.groupby("month_label", as_index=False).agg(
        revenue=("net_amount", "sum"), orders=("order_id", "nunique"))
    fig = px.line(monthly, x="month_label", y="revenue", markers=True,
                  title="Pendapatan bulanan", labels={"month_label": "Bulan", "revenue": "Pendapatan (Rp)"})
    st.plotly_chart(fig)

    c1, c2 = st.columns(2)
    campaign = load_sql("07_campaign_impact")
    fig = px.bar(campaign, x="index_vs_weekday", y="day_type", orientation="h", text="index_vs_weekday",
                 title="Dampak momen belanja (indeks vs hari kerja biasa = 100)",
                 labels={"index_vs_weekday": "Indeks pendapatan harian", "day_type": ""})
    fig.update_yaxes(categoryorder="category descending")
    c1.plotly_chart(fig)
    c1.caption("Dihitung dari seluruh data (tidak terpengaruh filter).")

    heat = (done.groupby(["day_name", "order_hour"])["order_id"].nunique()
            .unstack(fill_value=0).reindex(DAY_ORDER))
    fig = px.imshow(heat, aspect="auto", color_continuous_scale="Blues",
                    title="Pola waktu belanja (jumlah pesanan)", labels={"x": "Jam", "y": "", "color": "Pesanan"})
    c2.plotly_chart(fig)

# ---------------------------------------------------------------------------
# Tab Produk
# ---------------------------------------------------------------------------
with tab_product:
    c1, c2 = st.columns(2)
    by_brand = done.groupby("brand", as_index=False)["net_amount"].sum().sort_values("net_amount")
    fig = px.bar(by_brand, x="net_amount", y="brand", orientation="h", title="Pendapatan per brand",
                 labels={"net_amount": "Pendapatan (Rp)", "brand": ""})
    c1.plotly_chart(fig)

    by_cat = done.groupby("category", as_index=False)["net_amount"].sum()
    fig = px.pie(by_cat, names="category", values="net_amount", hole=0.5, title="Porsi pendapatan per kategori")
    c2.plotly_chart(fig)

    top = (done.groupby(["product_name", "brand"], as_index=False)
           .agg(units=("quantity", "sum"), revenue=("net_amount", "sum"))
           .sort_values("revenue", ascending=False).head(10))
    top["revenue"] = top["revenue"].map(rupiah)
    st.subheader("10 produk terlaris (berdasarkan pendapatan)")
    st.dataframe(top.rename(columns={"product_name": "Produk", "brand": "Brand", "units": "Unit terjual",
                                     "revenue": "Pendapatan"}), hide_index=True)

    c3, c4 = st.columns(2)
    tier = done.groupby("price_tier", as_index=False).agg(units=("quantity", "sum"), revenue=("net_amount", "sum"))
    fig = px.bar(tier, x="price_tier", y=["units"], title="Unit terjual per segmen harga",
                 labels={"price_tier": "Segmen harga", "value": "Unit"})
    fig.update_layout(showlegend=False)
    c3.plotly_chart(fig)

    ret = (delivered.groupby(["category", "order_id"])["is_returned"].max().groupby("category").mean() * 100
           ).reset_index(name="return_rate").sort_values("return_rate", ascending=False)
    fig = px.bar(ret, x="category", y="return_rate", title="Tingkat retur per kategori (%)",
                 labels={"category": "Kategori", "return_rate": "Retur (%)"})
    c4.plotly_chart(fig)

# ---------------------------------------------------------------------------
# Tab Pelanggan
# ---------------------------------------------------------------------------
with tab_customer:
    c1, c2 = st.columns(2)
    rfm = load_sql("03_rfm_segmentation")
    fig = px.bar(rfm, x="segment", y="revenue_share_pct", text="customers",
                 title="Segmen RFM: porsi pendapatan (%) & jumlah pelanggan",
                 labels={"segment": "Segmen", "revenue_share_pct": "Porsi pendapatan (%)"})
    c1.plotly_chart(fig)
    c1.caption("Dihitung dari seluruh data (tidak terpengaruh filter).")

    cities = (done[~done["city"].isin(["Tidak diketahui", "Lainnya"])]
              .groupby("city", as_index=False)["net_amount"].sum()
              .sort_values("net_amount", ascending=False).head(10).sort_values("net_amount"))
    fig = px.bar(cities, x="net_amount", y="city", orientation="h", title="10 kota dengan pendapatan terbesar",
                 labels={"net_amount": "Pendapatan (Rp)", "city": ""})
    c2.plotly_chart(fig)

    cohort = load_sql("04_cohort_retention")
    pivot = cohort[cohort["months_since_first"] <= 12].pivot(
        index="cohort", columns="months_since_first", values="retention_pct")
    fig = px.imshow(pivot, text_auto=".0f", aspect="auto", color_continuous_scale="Greens",
                    title="Cohort retention (%): pelanggan yang kembali belanja N bulan setelah pembelian pertama",
                    labels={"x": "Bulan sejak pembelian pertama", "y": "Cohort", "color": "Retensi %"})
    st.plotly_chart(fig)

    c3, c4 = st.columns(2)
    pay = load_sql("05_payment_method_trend")
    pay["year"] = pay["year"].astype(str)
    fig = px.bar(pay, x="year", y="share_pct", color="payment_method", barmode="group",
                 title="Pergeseran metode pembayaran (% pesanan)",
                 labels={"year": "Tahun", "share_pct": "Pangsa (%)", "payment_method": "Metode"})
    c3.plotly_chart(fig)

    age = done.groupby("age_group", as_index=False)["customer_key"].nunique()
    fig = px.bar(age, x="age_group", y="customer_key", title="Pelanggan aktif per kelompok usia",
                 labels={"age_group": "Usia", "customer_key": "Pelanggan"})
    c4.plotly_chart(fig)

# ---------------------------------------------------------------------------
# Tab Data Quality
# ---------------------------------------------------------------------------
with tab_dq:
    runs = load_table("SELECT * FROM etl_run_log ORDER BY started_at DESC")
    latest = runs.iloc[0]
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Status ETL terakhir", latest["status"])
    k2.metric("Baris diekstrak", f"{int(latest['rows_extracted']):,}".replace(",", "."))
    k3.metric("Baris ditolak/dibersihkan", f"{int(latest['rows_rejected']):,}".replace(",", "."))
    k4.metric("Durasi", f"{float(latest['duration_seconds']):.1f} detik")

    st.subheader("Hasil pemeriksaan kualitas data (run terakhir)")
    dq = load_table("SELECT check_name, table_name, severity, failed_rows, total_rows, failed_pct, action_taken "
                    "FROM data_quality_log WHERE run_id = :run_id", {"run_id": str(latest["run_id"])})
    st.dataframe(dq.rename(columns={"check_name": "Pemeriksaan", "table_name": "Tabel", "severity": "Status",
                                    "failed_rows": "Baris bermasalah", "total_rows": "Total baris",
                                    "failed_pct": "%", "action_taken": "Tindakan"}), hide_index=True)

    st.subheader("Riwayat eksekusi ETL")
    st.dataframe(runs[["run_id", "started_at", "status", "rows_extracted", "rows_rejected",
                       "rows_loaded_fact", "duration_seconds"]], hide_index=True)
