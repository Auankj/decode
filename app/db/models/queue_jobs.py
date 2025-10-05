import enum
from sqlalchemy import Column, Integer, String, DateTime, JSON, Index, Enum
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from datetime import datetime, timezone
from typing import Optional

from app.db.database import Base

class JobType(enum.Enum):
    """Job type enum."""
    NUDGE_CHECK = "NUDGE_CHECK"
    PROGRESS_CHECK = "PROGRESS_CHECK"
    AUTO_RELEASE_CHECK = "AUTO_RELEASE_CHECK"
    COMMENT_ANALYSIS = "COMMENT_ANALYSIS"

class JobStatus(enum.Enum):
    """Job status enum."""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    DEAD_LETTER = "DEAD_LETTER"

class QueueJob(Base):
    """
    Queue Jobs model as specified in MD file:
    queue_jobs table for managing background job processing
    """
    __tablename__ = "queue_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    job_type: Mapped[JobType] = mapped_column(
        Enum(JobType),
        nullable=False,
        index=True
    )
    payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # issue_id, claim_id, user_data, etc.
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )
    processed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus),
        default=JobStatus.PENDING,
        nullable=False,
        index=True
    )
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    def __repr__(self):
        return f"<QueueJob(id={self.id}, type='{self.job_type.value}', status='{self.status.value}')>"
