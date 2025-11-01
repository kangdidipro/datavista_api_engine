from fastapi import APIRouter, UploadFile, File, HTTPException, status
from fastapi.responses import JSONResponse
from typing import List
import pandas as pd
import io
import csv
import logging
import time
import json
from datetime import datetime
# Import Absolut yang sudah dikoreksi:
# from models.schemas import TransactionData
from database import bulk_insert_transactions, get_db_connection, create_initial_tables, create_summary_entry


router = APIRouter(prefix="/v1/import", tags=["CSV Bulk Import"])

@router.post("/csv")
async def import_csv_to_db(
    csv_file: UploadFile = File(..., description="File CSV untuk diimport"),
):
    """
    API 1: Menerima file CSV, memvalidasi, membersihkan, dan melakukan bulk insert.
    Menerapkan logic Pandas (pembersihan data, konversi tipe).
    """
    logging.warning("--- [DIAGNOSTIC] /v1/import/csv endpoint hit. Starting processing. ---")
    
    logging.warning(f"--- [DIAGNOSTIC] Menerima file: {csv_file.filename}, Tipe Konten: {csv_file.content_type} ---")
    
    if csv_file.content_type not in ["text/csv", "application/vnd.ms-excel", "application/octet-stream"]:
        raise HTTPException(status_code=400, detail="Hanya menerima format file CSV.")

    try:
        start_time = time.perf_counter()
        file_name = csv_file.filename
        


        # Membaca konten file ke memori (bytes)
        contents = await csv_file.read()
        
        # Menggunakan io.BytesIO untuk membaca ke Pandas DataFrame
        csv_buffer = io.BytesIO(contents)
        
        # --- 2. BACA CSV BERDASARKAN POSISI KOLOM ---
        # Mendefinisikan nama kolom sesuai urutan yang diharapkan di database
        column_names = [
            'transaction_id_asersi', 'tanggal', 'jam', 'mor', 'provinsi', 
            'kota_kabupaten', 'no_spbu', 'no_nozzle', 'no_dispenser', 
            'produk', 'volume_liter', 'penjualan_rupiah', 'operator', 
            'mode_transaksi', 'plat_nomor', 'nik', 'sektor_non_kendaraan', 
            'jumlah_roda_kendaraan', 'kuota', 'warna_plat'
        ]

        # Membaca CSV, melewati header, dan menerapkan nama kolom secara manual
        df = pd.read_csv(
            csv_buffer, 
            sep=';', 
            decimal=',', 
            header=None, 
            skiprows=1, 
            names=column_names
        )

        # --- 3. LOGIC PANDAS: Pembersihan Data dan Konversi Tipe ---
        
        # Konversi format tanggal dari DD/MM/YYYY ke YYYY-MM-DD
        df['tanggal'] = pd.to_datetime(df['tanggal'], format='%d/%m/%Y').dt.strftime('%Y-%m-%d')

        # Pastikan jumlah kolom sesuai skema (20 kolom)
        if df.shape[1] < 20:
            raise HTTPException(status_code=422, detail="Format CSV tidak valid: Jumlah kolom kurang dari 20.")


        # Mengonversi kolom ke tipe numerik, mengubah error menjadi NaN (Not a Number)
        df['volume_liter'] = pd.to_numeric(df['volume_liter'], errors='coerce')
        df['penjualan_rupiah'] = pd.to_numeric(df['penjualan_rupiah'], errors='coerce')
        df['mor'] = pd.to_numeric(df['mor'], errors='coerce')
        df['kuota'] = pd.to_numeric(df['kuota'], errors='coerce')

        # Menghapus duplikat berdasarkan kolom ID (transaction_id_asersi)
        df.drop_duplicates(subset=['transaction_id_asersi'], keep='first', inplace=True) 
        
        # Mengganti NaN dengan None (Wajib untuk insert Psycopg2/PostgreSQL)
        df = df.replace({pd.NA: None, float('nan'): None, '': None})
        
        # 3. PERSIAPAN DATA
        # Memastikan urutan kolom sesuai dengan yang diharapkan oleh 'bulk_insert_transactions'
        cols_for_insert = [
            'transaction_id_asersi', 'tanggal', 'jam', 'mor', 'provinsi', 
            'kota_kabupaten', 'no_spbu', 'no_nozzle', 'no_dispenser', 
            'produk', 'volume_liter', 'penjualan_rupiah', 'operator', 
            'mode_transaksi', 'plat_nomor', 'nik', 'sektor_non_kendaraan', 
            'jumlah_roda_kendaraan', 'kuota', 'warna_plat'
        ]
        # Menyelaraskan DataFrame dengan urutan kolom yang benar
        df_aligned = df[cols_for_insert]
        data_to_insert = [tuple(row) for row in df_aligned.values]

        # 4. MEMBUAT SUMMARY ENTRY
        # Lakukan agregasi untuk semua kolom summary yang baru
        total_volume = df['volume_liter'].sum()
        total_penjualan = df['penjualan_rupiah'].astype(float).sum() # Pastikan tipe data numerik

        # Hitung jumlah unik untuk kolom-kolom yang relevan
        total_operator = df['operator'].nunique()
        produk_jbt = df[df['produk'].isin(['BIO_SOLAR', 'PERTALITE'])]['produk'].nunique() # Contoh, sesuaikan dengan definisi JBT
        produk_jbkt = df[~df['produk'].isin(['BIO_SOLAR', 'PERTALITE'])]['produk'].nunique() # Contoh, sesuaikan dengan definisi JBKT

        total_volume_liter = df['volume_liter'].sum()
        total_penjualan_rupiah = df['penjualan_rupiah'].astype(float).sum()
        total_mode_transaksi = df['mode_transaksi'].nunique()
        total_plat_nomor = df['plat_nomor'].nunique()
        total_nik = df['nik'].nunique()
        total_sektor_non_kendaraan = df['sektor_non_kendaraan'].nunique()

        total_jumlah_roda_kendaraan_4 = df[df['jumlah_roda_kendaraan'] == '4']['jumlah_roda_kendaraan'].count()
        total_jumlah_roda_kendaraan_6 = df[df['jumlah_roda_kendaraan'] == '6']['jumlah_roda_kendaraan'].count()

        total_kuota = df['kuota'].sum()

        total_warna_plat_kuning = df[df['warna_plat'] == 'Kuning']['warna_plat'].count()
        total_warna_plat_hitam = df[df['warna_plat'] == 'Hitam']['warna_plat'].count()
        total_warna_plat_merah = df[df['warna_plat'] == 'Merah']['warna_plat'].count()
        total_warna_plat_putih = df[df['warna_plat'] == 'Putih']['warna_plat'].count()

        total_mor = df['mor'].nunique()
        total_provinsi = df['provinsi'].nunique()
        total_kota_kabupaten = df['kota_kabupaten'].nunique()
        total_no_spbu = df['no_spbu'].nunique()

        end_time = time.perf_counter()
        duration_ms = int((end_time - start_time) * 1000)

        summary_id = create_summary_entry(
            import_datetime=datetime.now(),
            import_duration=float(duration_ms / 1000), # Convert ms to seconds
            file_name=file_name,
            title=file_name, # Default title is the file name
            total_records_inserted=int(len(data_to_insert)),
            total_volume=float(total_volume),
            total_penjualan=str(total_penjualan), # Keep as string for now, adjust if needed
            total_operator=float(total_operator),
            produk_jbt=str(produk_jbt),
            produk_jbkt=str(produk_jbkt),
            total_volume_liter=float(total_volume_liter),
            total_penjualan_rupiah=str(total_penjualan_rupiah),
            total_mode_transaksi=str(total_mode_transaksi),
            total_plat_nomor=str(total_plat_nomor),
            total_nik=str(total_nik),
            total_sektor_non_kendaraan=str(total_sektor_non_kendaraan),
            total_jumlah_roda_kendaraan_4=str(total_jumlah_roda_kendaraan_4),
            total_jumlah_roda_kendaraan_6=str(total_jumlah_roda_kendaraan_6),
            total_kuota=float(total_kuota),
            total_warna_plat_kuning=str(total_warna_plat_kuning),
            total_warna_plat_hitam=str(total_warna_plat_hitam),
            total_warna_plat_merah=str(total_warna_plat_merah),
            total_warna_plat_putih=str(total_warna_plat_putih),
            total_mor=float(total_mor),
            total_provinsi=float(total_provinsi),
            total_kota_kabupaten=float(total_kota_kabupaten),
            total_no_spbu=float(total_no_spbu)
        )
        logging.warning(f"--- [DIAGNOSTIC] Created summary entry with ID: {summary_id} ---")

        # 5. EKSEKUSI BULK INSERT
        logging.warning("--- [DIAGNOSTIC] Calling bulk_insert_transactions ---")
        rows_inserted = bulk_insert_transactions(data_to_insert, summary_id)

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "message": "Import CSV berhasil diproses.",
                "total_rows_read": df.shape[0],
                "total_rows_inserted": rows_inserted,
                "summary_id": summary_id
            }
        )

    except Exception as e:
        # Log traceback lengkap untuk debugging di sisi server
        logging.error(f"Gagal memproses file: {e}", exc_info=True)
        
        # Kirim pesan error yang spesifik ke client untuk debugging
        error_type = type(e).__name__
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, 
            detail=f"Proses file gagal. Error Sebenarnya: [{error_type}] - {str(e)}"
        )
