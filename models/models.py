from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, ForeignKey, Numeric, ARRAY, JSON
)
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class AnomalyTemplateMaster(Base):
    __tablename__ = 'anomaly_template_master'
    template_id = Column(Integer, primary_key=True, index=True)
    role_name = Column(String, unique=True, nullable=False)
    description = Column(String)
    is_default = Column(Boolean, default=False)
    created_datetime = Column(DateTime, default=datetime.utcnow)
    last_modified = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String)

    # Relationships
    transaction_criteria = relationship("TransactionAnomalyCriteria", secondary="template_criteria_volume", back_populates="templates")
    special_criteria = relationship("SpecialAnomalyCriteria", secondary="template_criteria_special", back_populates="templates")
    video_parameters = relationship("VideoAiParameter", secondary="template_criteria_video", back_populates="templates")

class TransactionAnomalyCriteria(Base):
    __tablename__ = 'transaction_anomaly_criteria'
    criteria_id = Column(Integer, primary_key=True, index=True)
    anomaly_type = Column(String, nullable=False)
    min_volume_liter = Column(Integer, nullable=False)
    plate_color = Column(ARRAY(String))
    consumer_type = Column(String, nullable=False)
    description = Column(String)
    is_active = Column(Boolean, default=True)
    templates = relationship("AnomalyTemplateMaster", secondary="template_criteria_volume", back_populates="transaction_criteria")

class SpecialAnomalyCriteria(Base):
    __tablename__ = 'special_anomaly_criteria'
    special_criteria_id = Column(Integer, primary_key=True, index=True)
    criteria_code = Column(String, unique=True, nullable=False)
    criteria_name = Column(String, nullable=False)
    value = Column(String)
    unit = Column(String)
    violation_rule = Column(String, nullable=False)
    description = Column(String)
    templates = relationship("AnomalyTemplateMaster", secondary="template_criteria_special", back_populates="special_criteria")

class VideoAiParameter(Base):
    __tablename__ = 'video_ai_parameters'
    param_id = Column(Integer, primary_key=True, index=True)
    parameter_key = Column(String, unique=True, nullable=False)
    parameter_value = Column(Numeric(10, 3), nullable=False)
    unit = Column(String)
    module_name = Column(String, nullable=False)
    user_modifiable = Column(Boolean, default=True)
    last_modified_by = Column(String)
    templates = relationship("AnomalyTemplateMaster", secondary="template_criteria_video", back_populates="video_parameters")

# Linker Tables
class TemplateCriteriaVolume(Base):
    __tablename__ = 'template_criteria_volume'
    id = Column(Integer, primary_key=True)
    template_id = Column(Integer, ForeignKey('anomaly_template_master.template_id'))
    criteria_id = Column(Integer, ForeignKey('transaction_anomaly_criteria.criteria_id'))

class TemplateCriteriaSpecial(Base):
    __tablename__ = 'template_criteria_special'
    id = Column(Integer, primary_key=True)
    template_id = Column(Integer, ForeignKey('anomaly_template_master.template_id'))
    special_criteria_id = Column(Integer, ForeignKey('special_anomaly_criteria.special_criteria_id'))

class TemplateCriteriaVideo(Base):
    __tablename__ = 'template_criteria_video'
    id = Column(Integer, primary_key=True)
    template_id = Column(Integer, ForeignKey('anomaly_template_master.template_id'))
    param_id = Column(Integer, ForeignKey('video_ai_parameters.param_id'))

class LogManajemenFilterDtpa(Base):
    __tablename__ = 'log_manajemen_filter_dtpa'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    daily_summary_id = Column(Integer, nullable=False)
    template_id = Column(Integer, nullable=False)
    job_id = Column(String, unique=True, nullable=False)
    status = Column(String, default='QUEUED')
    total_anomalies_found = Column(Integer)
    anomalies_per_criteria = Column(JSON)
    processing_time_ms = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class HasilAnalisisDtpa(Base):
    __tablename__ = 'hasil_analisis_dtpa'
    id = Column(Integer, primary_key=True, index=True)
    log_id = Column(Integer, ForeignKey('log_manajemen_filter_dtpa.id'))
    transaction_id_asersi = Column(String)
    daily_summary_id = Column(Integer)
    template_id = Column(Integer)
    criteria_id_violated = Column(Integer)
    special_criteria_id_violated = Column(Integer)
    anomaly_datetime = Column(DateTime)
    anomaly_type = Column(String)
    violation_value = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

