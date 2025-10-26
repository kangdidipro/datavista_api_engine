# File: worker.py

import os
import time
import json
import uuid
from datetime import datetime
import psycopg2
from psycopg2 import sql, extras
import redis

import sys # <--- WAJIB: Tambahkan import sys di bagian atas file


# Asumsikan RQ (Redis Queue) sudah diinstal di Worker
from rq import Worker, Queue # Hapus Connection
from redis import Redis # Gunakan library redis untuk koneksi

# Import konfigurasi database (sama dengan yang digunakan FastAPI)
from db_config import POSTGRES_CONFIG, REDIS_CONFIG
from database import get_db_connection, create_initial_tables # Import logic DB

# --- FUNGSI UTILITY GPU WORKER (Simulasi Logika V7.37) ---

def simulate_gpu_analysis(video_path, task_type):
    """
    Simulasi pemrosesan video berat menggunakan YOLOv8 (Logic V7.37).
    Logic ini mencakup deteksi, OCR, dan perbaikan noise/parsing.
    """
    print(f"--- Processing Job: {task_type} ---")
    print(f"Analyzing file: {video_path}")
    
    # Simulasikan delay dan resource GPU
    time.sleep(3) 

    result = {
        "success": True,
        "detected_datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "detected_plat": "B1234XYZ" if task_type == "license-plate" else "N/A",
        "processing_time": 3.14,
        "worker_id": str(uuid.uuid4())[:8],
        # Logic V7.37: Memperbaiki noise dan error parsing
        "message": "Analysis successful. Logic V7.37 applied for stability." 
    }
    return result

def log_analysis_result(video_path, analysis_result, task_type):
    """Mencatat hasil analisis ke PostgreSQL."""
    
    # Asumsikan tabel log analisis sudah dibuat
    LOG_TABLE = "video_analysis_log" 

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                insert_query = f"""
                    INSERT INTO {LOG_TABLE} (
                        job_id, file_path, detected_datetime, detected_plat, 
                        status, message, worker_id, task_type
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s
                    )
                """
                cursor.execute(insert_query, (
                    analysis_result['job_id'],
                    video_path,
                    analysis_result['detected_datetime'],
                    analysis_result['detected_plat'],
                    'COMPLETED',
                    analysis_result['message'],
                    analysis_result['worker_id'],
                    task_type
                ))
                conn.commit()
                print(f"Result logged to DB successfully.")
                
    except Exception as e:
        print(f"FATAL: Could not log result to DB: {e}")
        # Dalam skenario nyata, job harus diantrikan kembali di sini
        return False
    
# --- FUNGSI UTAMA: MENANGANI JOB DARI QUEUE ---

def handle_video_job(job_payload_str):
    """Menerima job dari Redis dan menjalankan analisis."""
    
    try:
        job_payload = json.loads(job_payload_str)
        job_id = job_payload['job_id']
        video_path = job_payload['path']
        task_type = job_payload['task']
        
        print(f"JOB {job_id} received. Type: {task_type}")

        # 1. Jalankan Analisis (Simulasi YOLOv8/GPU)
        analysis_result = simulate_gpu_analysis(video_path, task_type)
        analysis_result['job_id'] = job_id
        
        # 2. Catat Hasil
        log_analysis_result(video_path, analysis_result, task_type)
        
        # 3. Hapus File Sementara (Setelah diproses)
        if os.path.exists(video_path):
            os.remove(video_path)
            print(f"Temporary file {video_path} deleted.")
        
        return True
        
    except Exception as e:
        print(f"Job processing failed for {job_id}: {e}")
        return False

# --- 4. START REDIS WORKER (Akan dijalankan di container GPU Worker) ---

def start_worker():
    """Menginisialisasi dan memulai RQ Worker."""

    # Koneksi ke Redis Broker (redis_broker)
    redis_conn = redis.Redis(host=REDIS_CONFIG['host'], port=REDIS_CONFIG['port'])

    # 1. INISIALISASI SKEMA DB (KOREKSI: HARUS DILAKUKAN UNTUK MEMBUAT TABEL LOG VIDEO)
    try:
        with get_db_connection() as conn:
            create_initial_tables(conn) # Membuat tabel log transaksi dan summary
            # TODO: Tambahkan logic untuk membuat tabel log analisis video di sini jika diperlukan
            print("Database Schema Verified for Worker.")
    except Exception as e:
        print(f"FATAL: Database initialization failed for worker: {e}")
        sys.exit(1) # Keluar jika gagal koneksi/skema

    # 2. START WORKER
    print("Starting DataVista GPU Worker...")
    with Connection(redis_conn):
        worker = Worker(['datavista_queue'], connection=redis_conn, default_timeout=3600) # Default timeout for long jobs
        worker.work()

        
if __name__ == '__main__':
    # Ini adalah entry point untuk container worker
    start_worker()
