from pydantic import BaseModel, Field
from datetime import date, time, datetime
from typing import Optional

# --- MODEL DATA INPUT CSV (Diperlukan untuk Validasi Pandas) ---
# Skema ini mencerminkan kolom dari file CSV Anda

class TransactionData(BaseModel):
    """
    Model untuk memvalidasi satu baris data transaksi dari CSV.
    """
    transaction_id_asersi: str = Field(..., max_length=50)
    tanggal: date = Field(..., description="Format: YYYY-MM-DD")
    jam: time = Field(..., description="Format: HH:MM:SS")
    mor: Optional[int] = Field(None)
    provinsi: str = Field(..., max_length=50)
    kota_kabupaten: str = Field(..., max_length=50)
    no_spbu: str = Field(..., max_length=20)
    no_nozzle: Optional[str] = Field(None, max_length=20)
    no_dispenser: Optional[str] = Field(None, max_length=50)
    produk: str = Field(..., max_length=50)
    volume_liter: float = Field(..., description="Volume harus berupa angka desimal.")
    penjualan_rupiah: str = Field(..., max_length=50)
    operator: Optional[str] = Field(None, max_length=50)
    mode_transaksi: Optional[str] = Field(None, max_length=50)
    plat_nomor: Optional[str] = Field(None, max_length=20)
    nik: Optional[str] = Field(None, max_length=30)
    sektor_non_kendaraan: Optional[str] = Field(None, max_length=50)
    jumlah_roda_kendaraan: Optional[str] = Field(None, max_length=50)
    kuota: Optional[float] = Field(None)
    warna_plat: Optional[str] = Field(None, max_length=20)


# --- MODEL LOG ANALISIS VIDEO ---

class VideoLogEntry(BaseModel):
    """
    Model yang digunakan Worker untuk mencatat hasil analisis video ke DB.
    """
    video_path: str = Field(..., description="Lokasi file video di storage.")
    log_datetime: Optional[datetime] = Field(None, description="Hasil deteksi datetime (YOLOv8).")
    detected_plat: Optional[str] = Field(None, max_length=20, description="Hasil deteksi plat nomor (YOLOv8 + OCR).")
    worker_id: str = Field(..., max_length=10)
    status: str = Field(..., max_length=20)
    message: Optional[str] = Field(None)
