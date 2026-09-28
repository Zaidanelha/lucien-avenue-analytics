-- 10 kota dengan pendapatan terbesar dan kontribusinya terhadap total.
-- Pelanggan tanpa alamat valid ('Tidak diketahui'/'Lainnya') tidak ikut diranking.
SELECT c.province,
       c.city,
       COUNT(DISTINCT f.customer_key) AS customers,
       COUNT(DISTINCT f.order_id)     AS orders,
       ROUND(SUM(f.net_amount), 0)    AS revenue,
       ROUND(SUM(f.net_amount) * 100.0
             / (SELECT SUM(net_amount) FROM fact_sales WHERE order_status = 'selesai'), 2) AS revenue_share_pct
FROM fact_sales f
JOIN dim_customer c ON c.customer_key = f.customer_key
WHERE f.order_status = 'selesai'
  AND c.city NOT IN ('Tidak diketahui', 'Lainnya')
GROUP BY c.province, c.city
ORDER BY revenue DESC
LIMIT 10;
