from sqlalchemy.orm import Session
from typing import List
from models import models, schemas

def get_templates(db: Session):
    return db.query(models.AnomalyTemplateMaster).order_by(models.AnomalyTemplateMaster.role_name).all()

def get_template(db: Session, template_id: int):
    return db.query(models.AnomalyTemplateMaster).filter(models.AnomalyTemplateMaster.template_id == template_id).first()

def create_template(db: Session, template: schemas.AnomalyTemplateMasterCreate):
    db_template = models.AnomalyTemplateMaster(**template.dict())
    db.add(db_template)
    db.commit()
    db.refresh(db_template)
    return db_template

def update_template_links(db: Session, template_id: int, volume_ids: List[int], special_ids: List[int], video_ids: List[int]):
    template = get_template(db, template_id)
    if not template:
        return None
    
    template.transaction_criteria = db.query(models.TransactionAnomalyCriteria).filter(models.TransactionAnomalyCriteria.criteria_id.in_(volume_ids)).all()
    template.special_criteria = db.query(models.SpecialAnomalyCriteria).filter(models.SpecialAnomalyCriteria.special_criteria_id.in_(special_ids)).all()
    template.video_parameters = db.query(models.VideoAiParameter).filter(models.VideoAiParameter.param_id.in_(video_ids)).all()
    
    db.commit()
    return template

def set_active_template(db: Session, template_id: int):
    db.query(models.AnomalyTemplateMaster).update({"is_default": False})
    db.query(models.AnomalyTemplateMaster).filter(models.AnomalyTemplateMaster.template_id == template_id).update({"is_default": True})
    db.commit()

def duplicate_template(db: Session, template_id: int):
    original = get_template(db, template_id)
    if not original:
        return None
    
    clone = models.AnomalyTemplateMaster(
        role_name=f"{original.role_name} (Copy)",
        description=original.description,
        is_default=False,
        created_by=original.created_by # Or current user
    )
    db.add(clone)
    db.commit()
    db.refresh(clone)

    clone.transaction_criteria = original.transaction_criteria
    clone.special_criteria = original.special_criteria
    clone.video_parameters = original.video_parameters
    db.commit()
    return clone

def delete_template(db: Session, template_id: int):
    template = get_template(db, template_id)
    if template:
    return template

# CRUD for SpecialAnomalyCriteria
def get_special_criteria(db: Session, special_criteria_id: int):
    return db.query(models.SpecialAnomalyCriteria).filter(models.SpecialAnomalyCriteria.special_criteria_id == special_criteria_id).first()

def get_all_special_criteria(db: Session):
    return db.query(models.SpecialAnomalyCriteria).all()

def create_special_criteria(db: Session, criteria: schemas.SpecialAnomalyCriteriaCreate):
    db_criteria = models.SpecialAnomalyCriteria(**criteria.dict())
    db.add(db_criteria)
    db.commit()
    db.refresh(db_criteria)
    return db_criteria

def update_special_criteria(db: Session, special_criteria_id: int, criteria: schemas.SpecialAnomalyCriteriaUpdate):
    db_criteria = get_special_criteria(db, special_criteria_id)
    if db_criteria:
        for key, value in criteria.dict(exclude_unset=True).items():
            setattr(db_criteria, key, value)
        db.commit()
        db.refresh(db_criteria)
    return db_criteria

def delete_special_criteria(db: Session, special_criteria_id: int):
    db_criteria = get_special_criteria(db, special_criteria_id)
    if db_criteria:
        db.delete(db_criteria)
        db.commit()
    return db_criteria

# CRUD for TransactionAnomalyCriteria
def get_transaction_criteria(db: Session, criteria_id: int):
    return db.query(models.TransactionAnomalyCriteria).filter(models.TransactionAnomalyCriteria.criteria_id == criteria_id).first()

def get_all_transaction_criteria(db: Session):
    return db.query(models.TransactionAnomalyCriteria).all()

def create_transaction_criteria(db: Session, criteria: schemas.TransactionAnomalyCriteriaCreate):
    db_criteria = models.TransactionAnomalyCriteria(**criteria.dict())
    db.add(db_criteria)
    db.commit()
    db.refresh(db_criteria)
    return db_criteria

def update_transaction_criteria(db: Session, criteria_id: int, criteria: schemas.TransactionAnomalyCriteriaUpdate):
    db_criteria = get_transaction_criteria(db, criteria_id)
    if db_criteria:
        for key, value in criteria.dict(exclude_unset=True).items():
            setattr(db_criteria, key, value)
        db.commit()
        db.refresh(db_criteria)
    return db_criteria

def delete_transaction_criteria(db: Session, criteria_id: int):
    db_criteria = get_transaction_criteria(db, criteria_id)
    if db_criteria:
        db.delete(db_criteria)
        db.commit()
    return db_criteria