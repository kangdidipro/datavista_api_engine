from db_config import POSTGRES_CONFIG
from contextlib import contextmanager
from typing import List, Tuple

from fastapi import HTTPException 
import psycopg2
from psycopg2 import sql, extras
import pandas as pd
import sys

# --- KONFIGURASI NAMA TABEL ---
TRANSACTION_TABLE = "csv_import_log"
SUMMARY_TABLE = "csv_summary_master_daily"

# --- 1. KONEKSI UTILITY (Context Manager) ---

@contextmanager
def get_db_connection(config=None): # <--- TAMBAHKAN ARGUMEN INI
    """
    Menyediakan koneksi Psycopg2 menggunakan context manager.
    Koneksi akan ditutup secara otomatis saat keluar dari blok 'with'.
    """
    conn = None

    # Koreksi: Set conn_config secara eksplisit di awal scope
    conn_config = config if config else POSTGRES_CONFI

    from fastapi import HTTPException
    
    try:
        conn = psycopg2.connect(**conn_config) # <--- GUNAKAN conn_config
        yield conn
    except psycopg2.Error as e:
        print(f"Database connection error: {e}")
        # HTTPException diimpor di dalam fungsi untuk menghindari conflict saat startup
        raise HTTPException(status_code=503, detail="Layanan Database tidak tersedia.")
    finally:
        if conn:
            conn.close()

# --- 2. LOGIC BULK INSERT TRANSAKSI CSV (Psycopg2) ---

def bulk_insert_transactions(data_tuples: List[Tuple], summary_id: int):
    """
    Melakukan bulk insert data transaksi ke PostgreSQL.
    Menggunakan teknik Psycopg2 execute_values untuk efisiensi.
    """
    # Kolom ini harus sesuai dengan urutan kolom dalam CSV dan model Anda (20 kolom + 1 FK)
    cols_for_insert = [
        'transaction_id_asersi', 'tanggal', 'jam', 'mor', 'provinsi', 
        'kota_kabupaten', 'no_spbu', 'no_nozzle', 'no_dispenser', 
        'produk', 'volume_liter', 'penjualan_rupiah', 'operator', 
        'mode_transaksi', 'plat_nomor', 'nik', 'sektor_non_kendaraan', 
        'jumlah_roda_kendaraan', 'kuota', 'warna_plat', 'daily_summary_id'
    ]
    
    # Menambahkan summary_id (FK) ke setiap baris
    data_with_fk = [item + (summary_id,) for item in data_tuples]
    
    # Query SQL: INSERT ... ON CONFLICT DO NOTHING (Mencegah duplikat ID)
    insert_query = sql.SQL("""
        INSERT INTO {} ({}) 
        VALUES %s
        ON CONFLICT (transaction_id_asersi) DO NOTHING
    """).format(
        sql.Identifier(TRANSACTION_TABLE),
        sql.SQL(', ').join(map(sql.Identifier, cols_for_insert))
    )

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Menggunakan execute_values untuk bulk insert yang efisien
                extras.execute_values(
                    cursor,
                    insert_query,
                    data_with_fk,
                    page_size=10000
                )
                conn.commit()
                # Mengembalikan jumlah baris yang berhasil diinsert
                return cursor.rowcount
    except Exception as e:
        print(f"Bulk insert failed: {e}")
        # Di sini kita tidak Raise HTTPException karena ini adalah logic worker/utility
        raise e

# --- 3. LOGIC PEMBUATAN TABEL AWAL (Untuk digunakan di Docker Entrypoint) ---

def create_initial_tables(conn):
    """Membuat tabel log transaksi dan summary jika belum ada."""

    # Jalankan kueri
    try:    
    
        # NOTE: Pastikan semua kolom dari cols_for_insert didefinisikan di sini
        cursor = conn.cursor()

        CREATE_TRANSACTION_LOG = sql.SQL("""
            CREATE TABLE IF NOT EXISTS {} (
                transaction_id_asersi VARCHAR(50) NOT NULL PRIMARY KEY,
                tanggal DATE NOT NULL,
                jam TIME NOT NULL,
                mor INT,
                provinsi VARCHAR(50),
                kota_kabupaten VARCHAR(50),
                no_spbu VARCHAR(20),
                no_nozzle VARCHAR(20),
                no_dispenser VARCHAR(50),
                produk VARCHAR(50),
                volume_liter DECIMAL(10,3),
                penjualan_rupiah VARCHAR(50),
                operator VARCHAR(50),
                mode_transaksi VARCHAR(50),
                plat_nomor VARCHAR(20),
                nik VARCHAR(30),
                sektor_non_kendaraan VARCHAR(50),
                jumlah_roda_kendaraan VARCHAR(50),
                kuota DECIMAL(10,1),
                warna_plat VARCHAR(20),
                daily_summary_id INT
                
                CONSTRAINT fk_daily_summary FOREIGN KEY (daily_summary_id) 
                    REFERENCES {} (summary_id) ON DELETE CASCADE
            );
        """).format(sql.Identifier(TRANSACTION_TABLE), sql.Identifier(SUMMARY_TABLE))

        CREATE_SUMMARY_MASTER = sql.SQL("""
            CREATE TABLE IF NOT EXISTS {} (
                summary_id SERIAL PRIMARY KEY,
                import_datetime TIMESTAMP NOT NULL,
                total_records_inserted INT,
                spbu_codes_found VARCHAR(500),
                total_volume DECIMAL(20,3),
                total_penjualan VARCHAR(50)
            );
        """).format(sql.Identifier(SUMMARY_TABLE))

        print(CREATE_TRANSACTION_LOG)
        
        # Jalankan kueri
        cursor.execute(CREATE_SUMMARY_MASTER)
        cursor.execute(CREATE_TRANSACTION_LOG)
        conn.commit()
        print("SCHEMAS CREATED SUCCESSFULLY") # Tanda keberhasilan

    except psycopg2.Error as e:
        # DEBUG KRITIS: Tampilkan error SQL sebenarnya
        sys.stderr.write(f"\n[FATAL SQL SYNTAX ERROR]\n{e.pgerror}\n")
        conn.rollback() # Batalkan transaksi jika ada error
        raise e # Re-raise error untuk menghentikan proses

    cursor.close()    
