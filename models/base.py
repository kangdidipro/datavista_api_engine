from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Database connection details from environment variables
POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'postgres_db')
POSTGRES_DB = os.getenv('POSTGRES_DB', 'datavista_db')
POSTGRES_USER = os.getenv('POSTGRES_USER', 'datavista_api_user')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'DatavistaAPI@2025')

SQLALCHEMY_DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:5432/{POSTGRES_DB}"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()