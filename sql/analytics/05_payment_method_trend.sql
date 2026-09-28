-- Pergeseran preferensi metode pembayaran per tahun (pangsa jumlah pesanan).
-- Teknik: window aggregate SUM() OVER (PARTITION BY ...).
WITH payment_orders AS (
    SELECT d.year,
           f.payment_method,
           COUNT(DISTINCT f.order_id) AS orders
    FROM fact_sales f
    JOIN dim_date d ON d.date_key = f.date_key
    WHERE f.order_status <> 'dibatalkan'
    GROUP BY d.year, f.payment_method
)
SELECT year,
       payment_method,
       orders,
       ROUND(orders * 100.0 / SUM(orders) OVER (PARTITION BY year), 2) AS share_pct
FROM payment_orders
ORDER BY year, orders DESC;
