from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, JSON, ForeignKey, Text, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os

Base = declarative_base()

# Database configuration - convert async URL to sync for old models
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://abhra:@localhost:5432/cookie_detector")
# Convert asyncpg URL to psycopg2 for sync operations
SYNC_DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
engine = create_engine(SYNC_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Database session dependency"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Import all models
from .repositories import Repository
from .issues import Issue
from .claims import Claim
from .activity_log import ActivityLog
from .progress_tracking import ProgressTracking
from .queue_jobs import QueueJob

__all__ = [
    "Base", "engine", "SessionLocal", "get_db",
    "Repository", "Issue", "Claim", "ActivityLog", 
    "ProgressTracking", "QueueJob"
]