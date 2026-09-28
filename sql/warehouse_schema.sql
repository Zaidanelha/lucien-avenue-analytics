-- =====================================================================
-- DATA WAREHOUSE (OLAP) - STAR SCHEMA
-- Grain fact_sales: satu baris per item pesanan.
-- Dijalankan ulang setiap ETL (full refresh). Kompatibel SQLite & MySQL 8.
-- =====================================================================

DROP TABLE IF EXISTS fact_sales;
DROP TABLE IF EXISTS dim_date;
DROP TABLE IF EXISTS dim_customer;
DROP TABLE IF EXISTS dim_product;

CREATE TABLE dim_date (
    date_key          INTEGER PRIMARY KEY,      -- format YYYYMMDD
    full_date         DATE NOT NULL,
    year              INTEGER NOT NULL,
    quarter           INTEGER NOT NULL,
    month             INTEGER NOT NULL,
    month_name        VARCHAR(20) NOT NULL,
    month_label       VARCHAR(7) NOT NULL,       -- YYYY-MM
    day               INTEGER NOT NULL,
    day_of_week       INTEGER NOT NULL,         -- 1 = Senin
    day_name          VARCHAR(10) NOT NULL,
    is_weekend        SMALLINT NOT NULL,
    is_payday_period  SMALLINT NOT NULL,        -- tanggal 25 s.d. 1
    is_harbolnas      SMALLINT NOT NULL,        -- 11.11 dan 12.12
    is_twin_date      SMALLINT NOT NULL,        -- 1.1, 2.2, ... 12.12
    is_ramadan        SMALLINT NOT NULL,
    day_number        INTEGER NOT NULL,         -- hari sejak 2000-01-01
    month_number      INTEGER NOT NULL          -- year * 12 + month
);

CREATE TABLE dim_customer (
    customer_key  INTEGER PRIMARY KEY,          -- surrogate key
    user_id       BIGINT NOT NULL,              -- natural key dari sistem sumber
    gender        VARCHAR(20) NOT NULL,
    age_group     VARCHAR(20) NOT NULL,
    city          VARCHAR(50) NOT NULL,
    province      VARCHAR(50) NOT NULL,
    signup_date   DATE
);

CREATE TABLE dim_product (
    product_key     INTEGER PRIMARY KEY,        -- surrogate key
    produk_id       BIGINT NOT NULL,            -- natural key dari sistem sumber
    product_name    VARCHAR(255) NOT NULL,
    model_name      VARCHAR(255) NOT NULL,
    brand           VARCHAR(50) NOT NULL,
    category        VARCHAR(50) NOT NULL,
    gender_segment  VARCHAR(20) NOT NULL,
    material        VARCHAR(50) NOT NULL,
    retail_price    DECIMAL(15, 2) NOT NULL,
    price_tier      VARCHAR(30) NOT NULL,
    release_date    DATE
);

CREATE TABLE fact_sales (
    order_item_id    BIGINT PRIMARY KEY,
    order_id         BIGINT NOT NULL,           -- degenerate dimension
    date_key         INTEGER NOT NULL,
    order_hour       SMALLINT NOT NULL,
    customer_key     INTEGER NOT NULL,
    product_key      INTEGER NOT NULL,
    quantity         INTEGER NOT NULL,
    unit_price       DECIMAL(15, 2) NOT NULL,
    gross_amount     DECIMAL(15, 2) NOT NULL,
    discount_amount  DECIMAL(15, 2) NOT NULL,
    net_amount       DECIMAL(15, 2) NOT NULL,
    promotion_code   VARCHAR(50) NOT NULL,
    order_status     VARCHAR(20) NOT NULL,
    payment_method   VARCHAR(50) NOT NULL,
    courier          VARCHAR(50) NOT NULL,
    is_returned      SMALLINT NOT NULL,
    return_reason    VARCHAR(100) NOT NULL,
    FOREIGN KEY (date_key) REFERENCES dim_date (date_key),
    FOREIGN KEY (customer_key) REFERENCES dim_customer (customer_key),
    FOREIGN KEY (product_key) REFERENCES dim_product (product_key)
);

CREATE INDEX idx_fact_date ON fact_sales (date_key);
CREATE INDEX idx_fact_customer ON fact_sales (customer_key);
CREATE INDEX idx_fact_product ON fact_sales (product_key);
CREATE INDEX idx_fact_status ON fact_sales (order_status);
