-- =====================================================================
-- SOURCE DATABASE (OLTP) - meniru skema database aplikasi Lucien Avenue
-- (diambil dari migration Laravel pada repo LUCIEN-AVENUE-BACKEND)
-- Kompatibel dengan SQLite dan MySQL 8 / MariaDB.
-- =====================================================================

DROP TABLE IF EXISTS returns;
DROP TABLE IF EXISTS shipments;
DROP TABLE IF EXISTS payments;
DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
    user_id        BIGINT PRIMARY KEY,
    first_name     VARCHAR(255) NOT NULL,
    last_name      VARCHAR(255),
    tanggal_lahir  DATE,
    alamat         TEXT,
    email          VARCHAR(255) NOT NULL,
    password       VARCHAR(255) NOT NULL,
    no_telepon     VARCHAR(50),
    jenis_kelamin  VARCHAR(50),
    created_at     DATETIME,
    updated_at     DATETIME
);

CREATE TABLE products (
    produk_id      BIGINT PRIMARY KEY,
    nama_sepatu    VARCHAR(255) NOT NULL,
    brand          VARCHAR(255),
    jenis          VARCHAR(255),
    material       VARCHAR(255),
    ukuran         VARCHAR(50) NOT NULL,
    warna          VARCHAR(100) NOT NULL,
    gender         VARCHAR(50),
    tanggal_rilis  DATE,
    sku            VARCHAR(100),
    harga_retail   DECIMAL(15, 2) NOT NULL,
    stok           INTEGER DEFAULT 0,
    created_at     DATETIME,
    updated_at     DATETIME
);

CREATE TABLE orders (
    pesanan_id      BIGINT PRIMARY KEY,
    user_id         BIGINT NOT NULL,
    jumlah_total    DECIMAL(15, 2) NOT NULL,
    subtotal        DECIMAL(15, 2) NOT NULL DEFAULT 0,
    discount        DECIMAL(15, 2) NOT NULL DEFAULT 0,
    promotion_code  VARCHAR(50),
    status_pesanan  VARCHAR(50) NOT NULL,
    created_at      DATETIME,
    updated_at      DATETIME,
    FOREIGN KEY (user_id) REFERENCES users (user_id)
);

CREATE TABLE order_items (
    barang_pesanan_id  BIGINT PRIMARY KEY,
    pesanan_id         BIGINT NOT NULL,
    produk_id          BIGINT NOT NULL,
    harga              DECIMAL(15, 2) NOT NULL,
    quantity           INTEGER NOT NULL,
    FOREIGN KEY (pesanan_id) REFERENCES orders (pesanan_id),
    FOREIGN KEY (produk_id) REFERENCES products (produk_id)
);

CREATE TABLE payments (
    pembayaran_id      BIGINT PRIMARY KEY,
    pesanan_id         BIGINT NOT NULL,
    metode_pembayaran  VARCHAR(100) NOT NULL,
    status_pembayaran  VARCHAR(50) NOT NULL,
    jumlah             DECIMAL(15, 2) NOT NULL,
    FOREIGN KEY (pesanan_id) REFERENCES orders (pesanan_id)
);

CREATE TABLE shipments (
    pengiriman_id         BIGINT PRIMARY KEY,
    pesanan_id            BIGINT NOT NULL,
    track_nomor           VARCHAR(100),
    metode_pengiriman     VARCHAR(100) NOT NULL,
    status_pengiriman     VARCHAR(50) NOT NULL,
    perkiraan_pengiriman  DATE,
    FOREIGN KEY (pesanan_id) REFERENCES orders (pesanan_id)
);

CREATE TABLE returns (
    pengembalian_id  BIGINT PRIMARY KEY,
    pesanan_id       BIGINT NOT NULL,
    pembelian        TEXT,
    pengembalian     TEXT,
    created_at       DATETIME,
    updated_at       DATETIME,
    FOREIGN KEY (pesanan_id) REFERENCES orders (pesanan_id)
);
