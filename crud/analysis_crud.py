from sqlalchemy.orm import Session
from sqlalchemy import func
from models import models
from datetime import datetime
from rq import get_current_job
import time

def run_anomaly_analysis(db: Session, job_id: str):
    job = get_current_job()
    start_time = time.time()

    # 1. Get job details from the log table
    job.meta['progress'] = 'Mempersiapkan analisis...'
    job.save_meta()
    log_entry = db.query(models.LogManajemenFilterDtpa).filter(models.LogManajemenFilterDtpa.job_id == job_id).first()
    if not log_entry:
        job.meta['progress'] = 'Error: Log entry not found.'
        job.save_meta()
        return

    log_entry.status = 'PROCESSING'
    db.commit()

    summary_id = log_entry.daily_summary_id
    template_id = log_entry.template_id
    template = db.query(models.AnomalyTemplateMaster).filter(models.AnomalyTemplateMaster.template_id == template_id).one()
    
    total_anomalies_found = 0
    anomalies_per_criteria = {}

    # Hapus hasil analisis lama untuk log ini
    db.query(models.HasilAnalisisDtpa).filter(models.HasilAnalisisDtpa.log_id == log_entry.id).delete()
    db.commit()

    total_rows_to_process = db.query(models.CsvImportLog).filter(models.CsvImportLog.daily_summary_id == summary_id).count()
    processed_rows = 0

    # 2. Single Transaction Analysis
    for criteria in template.transaction_criteria:
        if criteria.anomaly_type == 'SINGLE_TX':
            query = db.query(models.CsvImportLog).filter(
                models.CsvImportLog.daily_summary_id == summary_id,
                models.CsvImportLog.volume_liter > criteria.min_volume_liter,
                models.CsvImportLog.consumer_type == criteria.consumer_type
            ).yield_per(1000)

            for anomaly in query:
                processed_rows += 1
                job.meta['progress'] = f"Menganalisis... ({processed_rows}/{total_rows_to_process})"
                job.save_meta()

                new_result = models.HasilAnalisisDtpa(
                    log_id=log_entry.id,
                    transaction_id_asersi=anomaly.transaction_id_asersi,
                    daily_summary_id=summary_id,
                    template_id=template_id,
                    criteria_id_violated=criteria.criteria_id,
                    anomaly_datetime=datetime.combine(anomaly.tanggal, anomaly.jam),
                    anomaly_type=criteria.anomaly_type,
                    violation_value=str(anomaly.volume_liter)
                )
                db.add(new_result)
                total_anomalies_found += 1
                anomalies_per_criteria[f"vol_{criteria.criteria_id}"] = anomalies_per_criteria.get(f"vol_{criteria.criteria_id}", 0) + 1
                if processed_rows % 1000 == 0:
                    db.commit()

    # 4. Special Criteria Analysis
    for criteria in template.special_criteria:
        if criteria.criteria_code == 'NO_ID':
            query = db.query(models.CsvImportLog).filter(
                models.CsvImportLog.daily_summary_id == summary_id,
                (models.CsvImportLog.plat_nomor == None) | (models.CsvImportLog.nik == None)
            ).yield_per(1000)

            for anomaly in query:
                processed_rows += 1
                job.meta['progress'] = f"Menganalisis... ({processed_rows}/{total_rows_to_process})"
                job.save_meta()
                
                new_result = models.HasilAnalisisDtpa(
                    log_id=log_entry.id,
                    transaction_id_asersi=anomaly.transaction_id_asersi,
                    daily_summary_id=summary_id,
                    template_id=template_id,
                    special_criteria_id_violated=criteria.special_criteria_id,
                    anomaly_datetime=datetime.combine(anomaly.tanggal, anomaly.jam),
                    anomaly_type=criteria.criteria_code,
                    violation_value=None
                )
                db.add(new_result)
                total_anomalies_found += 1
                anomalies_per_criteria[f"spec_{criteria.special_criteria_id}"] = anomalies_per_criteria.get(f"spec_{criteria.special_criteria_id}", 0) + 1
                if processed_rows % 1000 == 0:
                    db.commit()

    db.commit()
    
    end_time = time.time()
    processing_time_ms = int((end_time - start_time) * 1000)

    log_entry.status = 'COMPLETED'
    log_entry.total_anomalies_found = total_anomalies_found
    log_entry.anomalies_per_criteria = anomalies_per_criteria
    log_entry.processing_time_ms = processing_time_ms
    db.commit()

    job.meta['progress'] = 'Selesai'
    job.save_meta()

    return {
        "total_anomalies": total_anomalies_found,
        "per_criteria": anomalies_per_criteria,
        "processing_time_ms": processing_time_ms
    }