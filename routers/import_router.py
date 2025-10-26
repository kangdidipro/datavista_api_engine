from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, status
from fastapi.responses import JSONResponse
from typing import List
import pandas as pd
import io
import csv
# Import Absolut yang sudah dikoreksi:
from models.schemas import TransactionData
from database import bulk_insert_transactions, get_db_connection, create_initial_tables


router = APIRouter(prefix="/v1/import", tags=["CSV Bulk Import"])

# --- DEPENDENCY: Memastikan Tabel Ada (Hanya untuk Dev/Testing) ---
# NOTE: Di produksi, tabel harus dibuat oleh Docker entrypoint.
# def initialize_db_schema():
#     """Membuat tabel jika belum ada."""
#     try:
#         with get_db_connection() as conn:
#             create_initial_tables(conn)
#     except Exception as e:
#         print(f"Schema initialization failed: {e}")
#         # Jika DB down, biarkan error terlempar saat koneksi
#         raise HTTPException(status_code=503, detail="Schema initialization failed.")


@router.post("/csv")
async def import_csv_to_db(
    csv_file: UploadFile = File(..., description="File CSV untuk diimport"),
    # Memastikan skema DB sudah ada saat pertama kali dijalankan
    # db_ready: None = Depends(initialize_db_schema) 
):
    """
    API 1: Menerima file CSV, memvalidasi, membersihkan, dan melakukan bulk insert.
    Menerapkan logic Pandas (pembersihan data, konversi tipe).
    """
    if csv_file.content_type not in ["text/csv", "application/vnd.ms-excel"]:
        raise HTTPException(status_code=400, detail="Hanya menerima format file CSV.")

    try:
        # Membaca konten file ke memori (bytes)
        contents = await csv_file.read()
        
        # Menggunakan io.BytesIO untuk membaca ke Pandas DataFrame
        csv_buffer = io.BytesIO(contents)
        
        # Membaca CSV ke Pandas (Skip header/baris 0)
        df = pd.read_csv(csv_buffer, header=None, skiprows=1)

        # 1. LOGIC PANDAS: Pembersihan Data dan Konversi Tipe
        
        # Pastikan jumlah kolom sesuai skema (20 kolom di TransactionData)
        if df.shape[1] < 20:
            raise HTTPException(status_code=422, detail="Format CSV tidak valid: Jumlah kolom kurang dari 20.")
        
        # Menghapus duplikat berdasarkan kolom ID (asumsi kolom 0 adalah ID)
        df.drop_duplicates(subset=[0], keep='first', inplace=True) 
        
        # Mengganti NaN dengan None (Wajib untuk insert Psycopg2/PostgreSQL)
        df = df.replace({pd.NA: None, float('nan'): None, '': None})
        
        # 3. PERSIAPAN BULK INSERT
        data_to_insert = [tuple(row) for row in df.values]

        # NOTE: Di sini kita akan memasukkan logic summary log yang hilang dari skrip lama.
        summary_id = 1 # Placeholder ID Master Log Summary yang harus dibuat terlebih dahulu
        
        # 4. EKSEKUSI BULK INSERT
        rows_inserted = bulk_insert_transactions(data_to_insert, summary_id)

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "message": "Import CSV berhasil diproses.",
                "total_rows_read": df.shape[0],
                "total_rows_inserted": rows_inserted
            }
        )

    except Exception as e:
        # Error pada level parsing atau database
        raise HTTPException(status_code=422, detail=f"Gagal memproses file: {e}")
