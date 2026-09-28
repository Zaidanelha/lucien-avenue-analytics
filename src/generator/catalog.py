"""Data referensi untuk generator: katalog sepatu, kota, dan kalender event.

Catatan: variasi penulisan kota (typo, singkatan, huruf besar/kecil) SENGAJA
dibuat supaya tahap ETL punya pekerjaan pembersihan data yang realistis.
"""
from datetime import date

# (nama model, brand, jenis, material, harga dasar IDR, popularitas relatif, colorway)
MODELS = [
    ("Air Jordan 1 Retro High OG", "Nike", "Basket", "Kulit", 3_100_000, 9, ["Chicago", "Bred", "Royal"]),
    ("Air Jordan 1 Low", "Nike", "Basket", "Kulit", 1_900_000, 10, ["White Wolf Grey", "Panda", "UNC"]),
    ("Air Jordan 4 Retro", "Nike", "Basket", "Kulit", 3_400_000, 6, ["Military Black", "White Cement"]),
    ("Air Force 1 '07", "Nike", "Lifestyle", "Kulit", 1_550_000, 12, ["Triple White", "Black"]),
    ("Dunk Low", "Nike", "Lifestyle", "Kulit", 1_650_000, 11, ["Panda", "Grey Fog", "Varsity Green"]),
    ("Air Max 90", "Nike", "Lifestyle", "Mesh", 2_100_000, 5, ["Infrared", "Triple Black"]),
    ("Pegasus 41", "Nike", "Lari", "Mesh", 1_950_000, 7, ["Black White", "Volt"]),
    ("Vomero 18", "Nike", "Lari", "Mesh", 2_300_000, 4, ["Sail", "Black"]),
    ("Samba OG", "Adidas", "Lifestyle", "Kulit", 1_800_000, 12, ["Cloud White", "Core Black"]),
    ("Gazelle Indoor", "Adidas", "Lifestyle", "Suede", 1_900_000, 8, ["Blue Bird", "Scarlet"]),
    ("Superstar", "Adidas", "Lifestyle", "Kulit", 1_500_000, 6, ["White Black", "Triple White"]),
    ("Campus 00s", "Adidas", "Lifestyle", "Suede", 1_700_000, 7, ["Core Black", "Grey"]),
    ("Ultraboost Light", "Adidas", "Lari", "Knit", 3_000_000, 5, ["Core Black", "Cloud White"]),
    ("Adizero Adios Pro 3", "Adidas", "Lari", "Mesh", 3_500_000, 3, ["Lucid Lemon", "Solar Red"]),
    ("530", "New Balance", "Lifestyle", "Mesh", 1_600_000, 10, ["White Silver", "Steel Grey"]),
    ("550", "New Balance", "Lifestyle", "Kulit", 1_900_000, 7, ["White Green", "White Navy"]),
    ("2002R", "New Balance", "Lifestyle", "Suede", 2_400_000, 5, ["Rain Cloud", "Protection Pack"]),
    ("990v6", "New Balance", "Lifestyle", "Suede", 4_300_000, 2, ["Grey"]),
    ("Fresh Foam X 1080v14", "New Balance", "Lari", "Mesh", 2_600_000, 3, ["Black", "White Blue"]),
    ("Palermo", "Puma", "Lifestyle", "Suede", 1_400_000, 7, ["Vapor Grey", "Green"]),
    ("Speedcat OG", "Puma", "Lifestyle", "Suede", 1_500_000, 6, ["Red White", "Black White"]),
    ("Velocity Nitro 3", "Puma", "Lari", "Mesh", 1_800_000, 3, ["Black", "Sunset"]),
    ("Chuck 70 Hi", "Converse", "Lifestyle", "Kanvas", 1_100_000, 9, ["Black", "Parchment"]),
    ("Run Star Hike", "Converse", "Lifestyle", "Kanvas", 1_400_000, 4, ["Black White"]),
    ("Old Skool", "Vans", "Skate", "Kanvas", 950_000, 10, ["Black White", "True White"]),
    ("Sk8-Hi", "Vans", "Skate", "Kanvas", 1_050_000, 5, ["Black White"]),
    ("Knu Skool", "Vans", "Skate", "Suede", 1_200_000, 5, ["Black", "Navy"]),
    ("Gel-Kayano 14", "Asics", "Lifestyle", "Mesh", 2_300_000, 6, ["Cream Silver", "White Midnight"]),
    ("Gel-1130", "Asics", "Lifestyle", "Mesh", 1_600_000, 6, ["White Pure Silver", "Black"]),
    ("Gel-Nimbus 26", "Asics", "Lari", "Mesh", 2_500_000, 4, ["Black Graphite", "White"]),
    ("Cloud 5", "On", "Lari", "Mesh", 2_300_000, 4, ["All Black", "Undyed White"]),
    ("Cloudmonster 2", "On", "Lari", "Mesh", 2_900_000, 3, ["Frost", "Black"]),
    # Rilisan premium / kolaborasi (harga tinggi, volume rendah)
    ("Air Jordan 1 Retro High OG Lost & Found", "Nike", "Basket", "Kulit", 7_950_000, 1, ["Chicago"]),
    ("Travis Scott x Air Jordan 1 Low", "Nike", "Basket", "Suede", 15_700_000, 0.5, ["Mocha", "Reverse Mocha"]),
    ("Off-White x Air Jordan 4", "Nike", "Basket", "Kulit", 22_000_000, 0.3, ["Sail"]),
]

# Model yang juga punya versi anak (GS), dengan harga ~60%
KIDS_MODELS = {"Air Jordan 1 Low", "Dunk Low", "Air Force 1 '07", "Samba OG", "Old Skool", "Chuck 70 Hi"}

# (kota kanonik, provinsi, bobot, variasi penulisan yang muncul di alamat pelanggan)
CITIES = [
    ("Jakarta Selatan", "DKI Jakarta", 7, ["Jaksel", "JAKARTA SELATAN", "Kota Jakarta Selatan", "jakarta selatan"]),
    ("Jakarta Barat", "DKI Jakarta", 5, ["Jakbar", "JAKARTA BARAT", "jakarta barat "]),
    ("Jakarta Timur", "DKI Jakarta", 5, ["Jaktim", "Kota Jakarta Timur"]),
    ("Jakarta Utara", "DKI Jakarta", 3, ["Jakut", "JAKARTA UTARA"]),
    ("Jakarta Pusat", "DKI Jakarta", 2, ["Jakpus", "jakarta pusat"]),
    ("Yogyakarta", "DI Yogyakarta", 7, ["Jogja", "Kota Yogyakarta", "YOGYAKARTA", "Yogya", "jogjakarta"]),
    ("Sleman", "DI Yogyakarta", 3, ["Kab. Sleman", "Kabupaten Sleman", "SLEMAN"]),
    ("Surabaya", "Jawa Timur", 8, ["SBY", "Kota Surabaya", "surabaya"]),
    ("Bandung", "Jawa Barat", 8, ["Kota Bandung", "BANDUNG", "bandung "]),
    ("Bekasi", "Jawa Barat", 5, ["Kota Bekasi", "BEKASI"]),
    ("Depok", "Jawa Barat", 4, ["Kota Depok"]),
    ("Bogor", "Jawa Barat", 4, ["Kota Bogor", "bogor"]),
    ("Tangerang", "Banten", 5, ["Kota Tangerang", "TANGERANG"]),
    ("Tangerang Selatan", "Banten", 4, ["Tangsel", "Kota Tangerang Selatan"]),
    ("Semarang", "Jawa Tengah", 4, ["Kota Semarang", "SEMARANG"]),
    ("Surakarta", "Jawa Tengah", 3, ["Solo", "Kota Surakarta", "SOLO"]),
    ("Malang", "Jawa Timur", 3, ["Kota Malang", "malang"]),
    ("Medan", "Sumatera Utara", 5, ["Kota Medan", "MEDAN"]),
    ("Palembang", "Sumatera Selatan", 2, ["Kota Palembang"]),
    ("Pekanbaru", "Riau", 2, ["Kota Pekanbaru"]),
    ("Batam", "Kepulauan Riau", 2, ["Kota Batam"]),
    ("Denpasar", "Bali", 3, ["Kota Denpasar", "DENPASAR"]),
    ("Makassar", "Sulawesi Selatan", 3, ["Kota Makassar", "MAKASSAR"]),
    ("Balikpapan", "Kalimantan Timur", 2, ["Kota Balikpapan"]),
]

PAYMENT_METHODS = ["Virtual Account", "GoPay", "ShopeePay", "QRIS", "Kartu Kredit"]
COURIERS = ["JNE", "J&T Express", "SiCepat", "AnterAja"]
RETURN_REASONS = ["Ukuran tidak sesuai", "Barang cacat", "Tidak sesuai deskripsi", "Berubah pikiran"]

# Periode Ramadan & tanggal Idulfitri (untuk pola musiman belanja)
RAMADAN_PERIODS = [
    (date(2024, 3, 11), date(2024, 4, 9), date(2024, 4, 10)),
    (date(2025, 3, 1), date(2025, 3, 30), date(2025, 3, 31)),
    (date(2026, 2, 18), date(2026, 3, 19), date(2026, 3, 20)),
]
