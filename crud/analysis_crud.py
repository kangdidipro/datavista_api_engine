from sqlalchemy.orm import Session
from sqlalchemy import func
from models import models
from datetime import datetime
from rq import get_current_job
import time
from typing import List
from crud import anomaly_execution_crud # Import the new CRUD

def run_anomaly_analysis(execution_id: str, summary_ids: List[int], db: Session):
    job = get_current_job()
    start_time = time.time()

    # 1. Get AnomalyExecution record
    execution = anomaly_execution_crud.get_anomaly_execution_by_id(db, execution_id)
    if not execution:
        job.meta['progress'] = 'Error: Anomaly Execution record not found.'
        job.save_meta()
        return

    anomaly_execution_crud.update_anomaly_execution_status(db, execution_id, 'PROCESSING')

    total_anomalies_found = 0
    anomalies_per_criteria = {}
    total_batches_processed_count = 0

    for summary_id in summary_ids:
        # Get the template associated with this execution
        template = db.query(models.AnomalyTemplateMaster).filter(models.AnomalyTemplateMaster.template_id == execution.template_id).one_or_none()
        if not template:
            # Handle error: template not found for this execution
            # For now, just skip this summary_id or log an error
            print(f"Error: Template with ID {execution.template_id} not found for execution {execution_id}")
            continue

        # Update batch status to PROCESSING
        batch_record = anomaly_execution_crud.create_anomaly_execution_batch(
            db=db,
            execution_id=execution_id,
            summary_id=summary_id,
            batch_status="PROCESSING"
        )

        total_rows_to_process = db.query(models.CsvImportLog).filter(models.CsvImportLog.daily_summary_id == summary_id).count()
        processed_rows = 0
        batch_anomalies_found = 0

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
                    job.meta['progress'] = f"Menganalisis Batch {summary_id}... ({processed_rows}/{total_rows_to_process})"
                    job.save_meta()

                    new_result = models.AnomalyResult( # Changed to AnomalyResult
                        execution_id=execution.execution_id, # Use execution_id
                        transaction_id_asersi=anomaly.transaction_id_asersi,
                        summary_id=summary_id,
                        template_id=template.template_id,
                        criteria_id_violated=criteria.criteria_id,
                        anomaly_datetime=datetime.combine(anomaly.tanggal, anomaly.jam),
                        anomaly_type=criteria.anomaly_type,
                        violation_value=str(anomaly.volume_liter)
                    )
                    db.add(new_result)
                    total_anomalies_found += 1
                    batch_anomalies_found += 1
                    anomalies_per_criteria[f"vol_{criteria.criteria_id}"] = anomalies_per_criteria.get(f"vol_{criteria.criteria_id}", 0) + 1
                    if processed_rows % 1000 == 0:
                        db.commit()

        # 3. Special Criteria Analysis
        for criteria in template.special_criteria:
            if criteria.criteria_code == 'NO_ID':
                query = db.query(models.CsvImportLog).filter(
                    models.CsvImportLog.daily_summary_id == summary_id,
                    (models.CsvImportLog.plat_nomor == None) | (models.CsvImportLog.nik == None)
                ).yield_per(1000)

                for anomaly in query:
                    processed_rows += 1
                    job.meta['progress'] = f"Menganalisis Batch {summary_id}... ({processed_rows}/{total_rows_to_process})"
                    job.save_meta()

                    parsed_date = datetime.strptime(anomaly.tanggal, '%Y-%m-%d').date()
                    parsed_time = datetime.strptime(anomaly.jam, '%H:%M:%S').time()
                    new_result = models.AnomalyResult( # Changed to AnomalyResult
                        execution_id=execution.execution_id, # Use execution_id
                        transaction_id_asersi=anomaly.transaction_id_asersi,
                        summary_id=summary_id,
                        template_id=template.template_id,
                        special_criteria_id_violated=criteria.special_criteria_id,
                        anomaly_datetime=datetime.combine(parsed_date, parsed_time),
                        anomaly_type=criteria.criteria_code,
                        violation_value=None
                    )
                    db.add(new_result)
                    total_anomalies_found += 1
                    batch_anomalies_found += 1
                    anomalies_per_criteria[f"spec_{criteria.special_criteria_id}"] = anomalies_per_criteria.get(f"spec_{criteria.special_criteria_id}", 0) + 1
                    if processed_rows % 1000 == 0:
                        db.commit()
            elif criteria.criteria_code == 'RED_PLATE': # P1: Plat Merah Dilarang
                query = db.query(models.CsvImportLog).filter(
                    models.CsvImportLog.daily_summary_id == summary_id,
                    models.CsvImportLog.warna_plat == 'MERAH'
                ).yield_per(1000)

                for anomaly in query:
                    processed_rows += 1
                    job.meta['progress'] = f"Menganalisis Batch {summary_id}... ({processed_rows}/{total_rows_to_process})"
                    job.save_meta()

                    parsed_date = datetime.strptime(anomaly.tanggal, '%Y-%m-%d').date()
                    parsed_time = datetime.strptime(anomaly.jam, '%H:%M:%S').time()
                    new_result = models.AnomalyResult(
                        execution_id=execution.execution_id,
                        transaction_id_asersi=anomaly.transaction_id_asersi,
                        summary_id=summary_id,
                        template_id=template.template_id,
                        special_criteria_id_violated=criteria.special_criteria_id,
                        anomaly_datetime=datetime.combine(parsed_date, parsed_time),
                        anomaly_type=criteria.criteria_code,
                        violation_value=anomaly.warna_plat
                    )
                    db.add(new_result)
                    total_anomalies_found += 1
                    batch_anomalies_found += 1
                    anomalies_per_criteria[f"spec_{criteria.special_criteria_id}"] = anomalies_per_criteria.get(f"spec_{criteria.special_criteria_id}", 0) + 1
                    if processed_rows % 1000 == 0:
                        db.commit()
        
        db.commit() # Commit any remaining changes for the current batch
        anomaly_execution_crud.update_anomaly_execution_batch_status(db, batch_record.detail_id, "COMPLETED", batch_anomalies_found)
        total_batches_processed_count += 1

    end_time = time.time()
    processing_time_ms = int((end_time - start_time) * 1000)

    anomaly_execution_crud.update_anomaly_execution_status(db, execution_id, 'COMPLETED', total_batches_processed_count)

    job.meta['progress'] = 'Selesai'
    job.save_meta()

    return {
        "total_anomalies": total_anomalies_found,
        "per_criteria": anomalies_per_criteria,
        "processing_time_ms": processing_time_ms
    }