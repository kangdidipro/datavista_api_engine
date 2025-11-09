from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, ForeignKey, Numeric, ARRAY, JSON, Time, BigInteger
)
from sqlalchemy.orm import relationship
from models.base import Base # Import Base from models.base
from datetime import datetime

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
    accumulated_criteria = relationship("AccumulatedAnomalyCriteria", secondary="template_criteria_accumulated", back_populates="templates")

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

class AccumulatedAnomalyCriteria(Base):
    __tablename__ = 'accumulated_anomaly_criteria'
    accumulated_criteria_id = Column(Integer, primary_key=True, index=True)
    criteria_code = Column(String, unique=True, nullable=False) # e.g., 'MAX_DAILY_VOLUME'
    criteria_name = Column(String, nullable=False)
    threshold_value = Column(Numeric(20, 3), nullable=False) # e.g., max volume
    time_window_hours = Column(Integer, default=24) # e.g., for daily accumulation
    group_by_field = Column(String, nullable=False) # e.g., 'plat_nomor', 'nik'
    description = Column(String)
    is_active = Column(Boolean, default=True)
    templates = relationship("AnomalyTemplateMaster", secondary="template_criteria_accumulated", back_populates="accumulated_criteria")

class TemplateCriteriaAccumulated(Base):
    __tablename__ = 'template_criteria_accumulated'
    id = Column(Integer, primary_key=True)
    template_id = Column(Integer, ForeignKey('anomaly_template_master.template_id'))
    accumulated_criteria_id = Column(Integer, ForeignKey('accumulated_anomaly_criteria.accumulated_criteria_id'))

class CsvSummaryMasterDaily(Base):
    __tablename__ = 'csv_summary_master_daily'
    summary_id = Column(BigInteger, primary_key=True, index=True) # Changed to BigInteger
    import_datetime = Column(DateTime, nullable=False)
    import_duration = Column(Numeric(20, 3))
    file_name = Column(String) # Removed length constraint
    title = Column(String) # Removed length constraint
    total_records_inserted = Column(Integer)
    total_records_read = Column(Integer)
    total_volume = Column(Numeric(20, 3))
    total_penjualan = Column(String) # Removed length constraint
    total_operator = Column(Numeric(20, 3))
    produk_jbt = Column(String) # Removed length constraint
    produk_jbkt = Column(String) # Removed length constraint
    total_volume_liter = Column(Numeric(10, 3))
    total_penjualan_rupiah = Column(String) # Removed length constraint
    total_mode_transaksi = Column(String) # Removed length constraint
    total_plat_nomor = Column(String) # Removed length constraint
    total_nik = Column(String) # Removed length constraint
    total_sektor_non_kendaraan = Column(String) # Removed length constraint
    total_jumlah_roda_kendaraan_4 = Column(String) # Removed length constraint
    total_jumlah_roda_kendaraan_6 = Column(String) # Removed length constraint
    total_kuota = Column(Numeric(10, 1))
    total_warna_plat_kuning = Column(String) # Removed length constraint
    total_warna_plat_hitam = Column(String) # Removed length constraint
    total_warna_plat_merah = Column(String) # Removed length constraint
    total_warna_plat_putih = Column(String) # Removed length constraint
    total_mor = Column(Numeric(20, 3))
    total_provinsi = Column(Numeric(20, 3))
    total_kota_kabupaten = Column(Numeric(20, 3))
    total_no_spbu = Column(Numeric(20, 3))
    numeric_totals = Column(JSON)

class CsvImportLog(Base):
    __tablename__ = 'csv_import_log'
    id = Column(BigInteger, primary_key=True, index=True)
    transaction_id_asersi = Column(String(50), unique=True, nullable=False)
    tanggal = Column(String, nullable=False)
    jam = Column(String, nullable=False)
    mor = Column(String) # Corrected to String
    provinsi = Column(String) # Removed length constraint
    kota_kabupaten = Column(String) # Removed length constraint
    no_spbu = Column(String) # Removed length constraint
    no_nozzle = Column(String) # Removed length constraint
    no_dispenser = Column(String) # Removed length constraint
    produk = Column(String) # Removed length constraint
    volume_liter = Column(Numeric(10, 3))
    penjualan_rupiah = Column(Numeric(15, 2))
    operator = Column(String) # Removed length constraint
    mode_transaksi = Column(String) # Removed length constraint
    plat_nomor = Column(String) # Removed length constraint
    nik = Column(String) # Removed length constraint
    sektor_non_kendaraan = Column(String) # Removed length constraint
    jumlah_roda_kendaraan = Column(String) # Removed length constraint
    kuota = Column(String) # Corrected to String
    warna_plat = Column(String) # Removed length constraint
    daily_summary_id = Column(BigInteger, ForeignKey('csv_summary_master_daily.summary_id'))
    import_attempt_count = Column(Integer, default=1)
    batch_original_duplicate_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    summary = relationship("CsvSummaryMasterDaily")

class TabelMor(Base):
    __tablename__ = 'tabel_mor'
    mor_id = Column(Integer, primary_key=True, index=True)
    mor = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

