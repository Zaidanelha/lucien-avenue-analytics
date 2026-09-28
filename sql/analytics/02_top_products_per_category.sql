-- 3 produk dengan pendapatan tertinggi di setiap kategori.
-- Teknik: window function ROW_NUMBER() dengan PARTITION BY.
WITH product_sales AS (
    SELECT p.category,
           p.product_name,
           p.brand,
           SUM(f.quantity)   AS units_sold,
           SUM(f.net_amount) AS revenue
    FROM fact_sales f
    JOIN dim_product p ON p.product_key = f.product_key
    WHERE f.order_status = 'selesai'
    GROUP BY p.category, p.product_name, p.brand
),
ranked AS (
    SELECT category, product_name, brand, units_sold, revenue,
           ROW_NUMBER() OVER (PARTITION BY category ORDER BY revenue DESC) AS rank_in_category
    FROM product_sales
)
SELECT category, rank_in_category, product_name, brand, units_sold, ROUND(revenue, 0) AS revenue
FROM ranked
WHERE rank_in_category <= 3
ORDER BY category, rank_in_category;
