-- Segmentasi pelanggan RFM (Recency, Frequency, Monetary).
-- Setiap dimensi diberi skor 1-5 dengan NTILE, lalu dipetakan ke segmen bisnis.
WITH snapshot AS (
    SELECT MAX(d.day_number) + 1 AS snapshot_day
    FROM fact_sales f
    JOIN dim_date d ON d.date_key = f.date_key
),
customer_metrics AS (
    SELECT f.customer_key,
           s.snapshot_day - MAX(d.day_number) AS recency_days,
           COUNT(DISTINCT f.order_id)         AS frequency,
           SUM(f.net_amount)                  AS monetary
    FROM fact_sales f
    JOIN dim_date d ON d.date_key = f.date_key
    CROSS JOIN snapshot s
    WHERE f.order_status = 'selesai'
    GROUP BY f.customer_key, s.snapshot_day
),
scored AS (
    SELECT customer_key, recency_days, frequency, monetary,
           NTILE(5) OVER (ORDER BY recency_days DESC)       AS r_score,
           NTILE(5) OVER (ORDER BY frequency, monetary)     AS f_score,
           NTILE(5) OVER (ORDER BY monetary)                AS m_score
    FROM customer_metrics
),
segmented AS (
    SELECT customer_key, recency_days, frequency, monetary, r_score, f_score, m_score,
           CASE
               WHEN r_score >= 4 AND f_score >= 4 THEN 'Champions'
               WHEN r_score >= 3 AND f_score >= 3 THEN 'Loyal Customers'
               WHEN r_score >= 4 AND f_score <= 2 THEN 'New / Promising'
               WHEN r_score <= 2 AND f_score >= 3 THEN 'At Risk'
               WHEN r_score <= 2 AND f_score <= 2 THEN 'Hibernating'
               ELSE 'Need Attention'
           END AS segment
    FROM scored
)
SELECT segment,
       COUNT(*)                     AS customers,
       ROUND(AVG(recency_days), 1)  AS avg_recency_days,
       ROUND(AVG(frequency), 2)     AS avg_frequency,
       ROUND(AVG(monetary), 0)      AS avg_monetary,
       ROUND(SUM(monetary) * 100.0 / (SELECT SUM(monetary) FROM segmented), 2) AS revenue_share_pct
FROM segmented
GROUP BY segment
ORDER BY SUM(monetary) DESC;
