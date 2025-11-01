from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict

from database import get_db
from models import schemas
from crud import anomaly_crud, analysis_crud

router = APIRouter(
    prefix="/api/anomaly-config",
    tags=["Anomaly Configuration"],
)

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict
from redis import Redis
from rq import Queue

from database import get_db
from models import schemas
from crud import anomaly_crud, analysis_crud

router = APIRouter(
    prefix="/api/anomaly-config",
    tags=["Anomaly Configuration"],
)

# Redis Queue Connection
redis_conn = Redis.from_url('redis://localhost:6379')
q = Queue(connection=redis_conn)

@router.post("/analyze/{summary_id}", status_code=202)
def start_analysis(summary_id: int, request: schemas.AnalysisRequest, db: Session = Depends(get_db)):
    if not request.template_id:
        raise HTTPException(status_code=422, detail="Missing required parameter: template_id")

    template_to_use = db.query(schemas.AnomalyTemplateMaster).filter(schemas.AnomalyTemplateMaster.template_id == request.template_id).first()
    if not template_to_use:
        raise HTTPException(status_code=404, detail=f"Template with id {request.template_id} not found.")

    job = q.enqueue(analysis_crud.run_anomaly_analysis, db, job.id, job_timeout=3600)
    return {"job_id": job.id}

@router.get("/analyze/status/{job_id}")
def get_analysis_status(job_id: str):
    job = q.fetch_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    
    response = {
        "job_id": job.id,
        "status": job.get_status(),
        "progress": job.meta.get('progress', 'Menunggu...'),
        "total_rows": job.meta.get('total_rows', 0),
    }
    if job.is_finished:
        response["result"] = job.result
    elif job.is_failed:
        response["error"] = job.exc_info
    
    return response


@router.get("/templates", response_model=List[schemas.AnomalyTemplateMaster])
def get_templates(db: Session = Depends(get_db)):
    return anomaly_crud.get_templates(db)

@router.get("/templates/{template_id}")
def get_template_details(template_id: int, db: Session = Depends(get_db)):
    template = anomaly_crud.get_template(db, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return {
        "template": template,
        "available_volume": db.query(schemas.TransactionAnomalyCriteria).all(),
        "available_special": db.query(schemas.SpecialAnomalyCriteria).all(),
        "available_video": db.query(schemas.VideoAiParameter).all(),
    }

@router.post("/templates", response_model=schemas.AnomalyTemplateMaster, status_code=201)
def create_template(template: schemas.AnomalyTemplateMasterCreate, db: Session = Depends(get_db)):
    return anomaly_crud.create_template(db=db, template=template)

@router.put("/templates/{template_id}")
def update_template(template_id: int, links: Dict[str, List[int]], db: Session = Depends(get_db)):
    updated = anomaly_crud.update_template_links(db, template_id, links.get('volume_ids', []), links.get('special_ids', []), links.get('video_ids', []))
    if not updated:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"message": "Template updated successfully."}

@router.patch("/templates/{template_id}/set-active")
def set_active(template_id: int, db: Session = Depends(get_db)):
    anomaly_crud.set_active_template(db, template_id)
    return {"message": "Active template switched successfully."}

@router.post("/templates/{template_id}/duplicate", response_model=schemas.AnomalyTemplateMaster, status_code=201)
def duplicate_template(template_id: int, db: Session = Depends(get_db)):
    new_template = anomaly_crud.duplicate_template(db, template_id)
    if not new_template:
        raise HTTPException(status_code=404, detail="Template not found")
    return new_template

@router.delete("/templates/{template_id}")
def delete_template(template_id: int, db: Session = Depends(get_db)):
    deleted = anomaly_crud.delete_template(db, template_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"message": "Template deleted successfully."}
