-- Pendapatan bulanan (pesanan selesai) beserta pertumbuhan MoM & YoY.
-- Teknik: CTE + window function LAG.
WITH monthly AS (
    SELECT d.month_label,
           d.year,
           d.month,
           COUNT(DISTINCT f.order_id) AS total_orders,
           SUM(f.net_amount)          AS revenue
    FROM fact_sales f
    JOIN dim_date d ON d.date_key = f.date_key
    WHERE f.order_status = 'selesai'
    GROUP BY d.month_label, d.year, d.month
)
SELECT month_label,
       total_orders,
       ROUND(revenue, 0)                AS revenue,
       ROUND(revenue / total_orders, 0) AS avg_order_value,
       ROUND((revenue - LAG(revenue) OVER (ORDER BY year, month)) * 100.0
             / LAG(revenue) OVER (ORDER BY year, month), 2)         AS mom_growth_pct,
       ROUND((revenue - LAG(revenue, 12) OVER (ORDER BY year, month)) * 100.0
             / LAG(revenue, 12) OVER (ORDER BY year, month), 2)     AS yoy_growth_pct
FROM monthly
ORDER BY year, month;
