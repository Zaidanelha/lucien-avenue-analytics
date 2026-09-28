-- Dampak momen belanja (Harbolnas, tanggal kembar, Ramadan, gajian) terhadap penjualan harian.
-- index_vs_weekday = 100 berarti sama dengan hari kerja biasa.
WITH daily AS (
    SELECT d.date_key, d.is_harbolnas, d.is_twin_date, d.is_ramadan, d.is_payday_period, d.is_weekend,
           COUNT(DISTINCT CASE WHEN f.order_status = 'selesai' THEN f.order_id END)  AS orders,
           SUM(CASE WHEN f.order_status = 'selesai' THEN f.net_amount ELSE 0 END)     AS revenue
    FROM dim_date d
    LEFT JOIN fact_sales f ON f.date_key = d.date_key
    GROUP BY d.date_key, d.is_harbolnas, d.is_twin_date, d.is_ramadan, d.is_payday_period, d.is_weekend
),
labeled AS (
    SELECT CASE
               WHEN is_harbolnas = 1     THEN '1. Harbolnas (11.11 & 12.12)'
               WHEN is_twin_date = 1     THEN '2. Tanggal kembar lainnya'
               WHEN is_ramadan = 1       THEN '3. Ramadan'
               WHEN is_payday_period = 1 THEN '4. Periode gajian (25-1)'
               WHEN is_weekend = 1       THEN '5. Akhir pekan biasa'
               ELSE '6. Hari kerja biasa'
           END AS day_type,
           orders, revenue
    FROM daily
)
SELECT day_type,
       COUNT(*)                AS days,
       ROUND(AVG(orders), 1)   AS avg_daily_orders,
       ROUND(AVG(revenue), 0)  AS avg_daily_revenue,
       ROUND(AVG(revenue) * 100.0
             / (SELECT AVG(revenue) FROM labeled WHERE day_type = '6. Hari kerja biasa'), 1) AS index_vs_weekday
FROM labeled
GROUP BY day_type
ORDER BY day_type;
