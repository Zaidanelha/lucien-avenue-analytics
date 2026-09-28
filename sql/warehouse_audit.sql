-- =====================================================================
-- TABEL AUDIT - tidak dihapus antar-run, sehingga riwayat ETL tersimpan.
-- =====================================================================

CREATE TABLE IF NOT EXISTS etl_run_log (
    run_id            VARCHAR(20) PRIMARY KEY,
    started_at        DATETIME NOT NULL,
    finished_at       DATETIME,
    status            VARCHAR(20) NOT NULL,
    rows_extracted    INTEGER,
    rows_rejected     INTEGER,
    rows_loaded_fact  INTEGER,
    duration_seconds  DECIMAL(10, 2),
    message           VARCHAR(500)
);

CREATE TABLE IF NOT EXISTS data_quality_log (
    run_id        VARCHAR(20) NOT NULL,
    check_name    VARCHAR(100) NOT NULL,
    table_name    VARCHAR(50) NOT NULL,
    severity      VARCHAR(10) NOT NULL,
    failed_rows   INTEGER NOT NULL,
    total_rows    INTEGER NOT NULL,
    failed_pct    DECIMAL(7, 3) NOT NULL,
    action_taken  VARCHAR(200) NOT NULL
);

CREATE TABLE IF NOT EXISTS quarantine_order_items (
    run_id             VARCHAR(20) NOT NULL,
    barang_pesanan_id  BIGINT NOT NULL,
    pesanan_id         BIGINT NOT NULL,
    produk_id          BIGINT NOT NULL,
    harga              DECIMAL(15, 2) NOT NULL,
    quantity           INTEGER NOT NULL,
    reason             VARCHAR(100) NOT NULL
);
