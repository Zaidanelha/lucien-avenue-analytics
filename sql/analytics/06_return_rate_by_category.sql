-- Tingkat retur per kategori produk & alasan retur paling dominan.
WITH delivered AS (
    SELECT p.category, f.order_id, MAX(f.is_returned) AS is_returned
    FROM fact_sales f
    JOIN dim_product p ON p.product_key = f.product_key
    WHERE f.order_status IN ('selesai', 'dikembalikan')
    GROUP BY p.category, f.order_id
)
SELECT category,
       COUNT(*)                                        AS delivered_orders,
       SUM(is_returned)                                AS returned_orders,
       ROUND(SUM(is_returned) * 100.0 / COUNT(*), 2)   AS return_rate_pct
FROM delivered
GROUP BY category
ORDER BY return_rate_pct DESC;
