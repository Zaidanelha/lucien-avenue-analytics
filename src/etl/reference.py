"""Data referensi (master data) yang dipakai ETL untuk standarisasi."""
from datetime import date

# Kota kanonik -> provinsi
CITY_PROVINCE = {
    "Jakarta Selatan": "DKI Jakarta", "Jakarta Barat": "DKI Jakarta", "Jakarta Timur": "DKI Jakarta",
    "Jakarta Utara": "DKI Jakarta", "Jakarta Pusat": "DKI Jakarta",
    "Yogyakarta": "DI Yogyakarta", "Sleman": "DI Yogyakarta",
    "Surabaya": "Jawa Timur", "Malang": "Jawa Timur",
    "Bandung": "Jawa Barat", "Bekasi": "Jawa Barat", "Depok": "Jawa Barat", "Bogor": "Jawa Barat",
    "Tangerang": "Banten", "Tangerang Selatan": "Banten",
    "Semarang": "Jawa Tengah", "Surakarta": "Jawa Tengah",
    "Medan": "Sumatera Utara", "Palembang": "Sumatera Selatan", "Pekanbaru": "Riau",
    "Batam": "Kepulauan Riau", "Denpasar": "Bali", "Makassar": "Sulawesi Selatan",
    "Balikpapan": "Kalimantan Timur",
}

# Singkatan / nama populer -> kota kanonik (key sudah lowercase)
CITY_ALIASES = {
    "jaksel": "Jakarta Selatan", "jakbar": "Jakarta Barat", "jaktim": "Jakarta Timur",
    "jakut": "Jakarta Utara", "jakpus": "Jakarta Pusat",
    "jogja": "Yogyakarta", "yogya": "Yogyakarta", "jogjakarta": "Yogyakarta",
    "sby": "Surabaya", "solo": "Surakarta", "tangsel": "Tangerang Selatan",
}

CITY_PREFIXES = ("kota ", "kabupaten ", "kab. ", "kab ")

GENDER_MAP = {
    "pria": "Pria", "l": "Pria", "laki-laki": "Pria", "laki laki": "Pria",
    "wanita": "Wanita", "p": "Wanita", "perempuan": "Wanita",
}

BRAND_CANONICAL = {
    "nike": "Nike", "adidas": "Adidas", "new balance": "New Balance", "puma": "Puma",
    "converse": "Converse", "vans": "Vans", "asics": "Asics", "on": "On",
}

# Akun internal/testing tidak boleh ikut dihitung sebagai penjualan
INTERNAL_EMAIL_DOMAINS = ("lucien.com", "test.com")

RAMADAN_PERIODS = [
    (date(2024, 3, 11), date(2024, 4, 9)),
    (date(2025, 3, 1), date(2025, 3, 30)),
    (date(2026, 2, 18), date(2026, 3, 19)),
]

MONTH_NAMES = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli",
               "Agustus", "September", "Oktober", "November", "Desember"]
DAY_NAMES = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]

UNKNOWN = "Tidak diketahui"
OTHER = "Lainnya"
