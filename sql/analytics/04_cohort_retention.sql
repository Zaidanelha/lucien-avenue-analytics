-- Analisis cohort: dari pelanggan yang pertama kali belanja di bulan X,
-- berapa persen yang belanja lagi 1, 2, 3, ... bulan kemudian.
WITH customer_months AS (
    SELECT f.customer_key, d.month_number
    FROM fact_sales f
    JOIN dim_date d ON d.date_key = f.date_key
    WHERE f.order_status = 'selesai'
    GROUP BY f.customer_key, d.month_number
),
first_purchase AS (
    SELECT customer_key, MIN(month_number) AS cohort_month_number
    FROM customer_months
    GROUP BY customer_key
),
cohort_activity AS (
    SELECT fp.cohort_month_number,
           cm.month_number - fp.cohort_month_number AS months_since_first,
           COUNT(DISTINCT cm.customer_key)          AS active_customers
    FROM customer_months cm
    JOIN first_purchase fp ON fp.customer_key = cm.customer_key
    GROUP BY fp.cohort_month_number, cm.month_number - fp.cohort_month_number
),
cohort_size AS (
    SELECT cohort_month_number, active_customers AS cohort_size
    FROM cohort_activity
    WHERE months_since_first = 0
),
month_labels AS (
    SELECT DISTINCT month_number, month_label FROM dim_date
)
SELECT ml.month_label AS cohort,
       cs.cohort_size,
       ca.months_since_first,
       ca.active_customers,
       ROUND(ca.active_customers * 100.0 / cs.cohort_size, 2) AS retention_pct
FROM cohort_activity ca
JOIN cohort_size cs  ON cs.cohort_month_number = ca.cohort_month_number
JOIN month_labels ml ON ml.month_number = ca.cohort_month_number
ORDER BY ca.cohort_month_number, ca.months_since_first;
