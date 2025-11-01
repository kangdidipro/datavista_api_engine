from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class AnomalyTemplateMasterBase(BaseModel):
    role_name: str
    description: Optional[str] = None
    is_default: bool = False
    created_by: Optional[str] = None

class AnomalyTemplateMasterCreate(AnomalyTemplateMasterBase):
    pass

class AnomalyTemplateMaster(AnomalyTemplateMasterBase):
    template_id: int
    created_datetime: datetime
    last_modified: datetime

    class Config:
        orm_mode = True

class TransactionAnomalyCriteria(BaseModel):
    criteria_id: int
    anomaly_type: str
    min_volume_liter: int
    plate_color: Optional[List[str]] = None
    consumer_type: str
    description: Optional[str] = None
    is_active: bool

    class Config:
        orm_mode = True

class SpecialAnomalyCriteria(BaseModel):
    special_criteria_id: int
    criteria_code: str
    criteria_name: str
    value: Optional[str] = None
    unit: Optional[str] = None
    violation_rule: str
    description: Optional[str] = None

    class Config:
        orm_mode = True



class AnalysisRequest(BaseModel):
    template_id: Optional[int] = None