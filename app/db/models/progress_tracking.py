import enum
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func
from datetime import datetime, timezone
from typing import Optional

from app.db.database import Base

class PRStatus(enum.Enum):
    """Pull request status enum."""
    OPEN = "open"
    CLOSED = "closed"
    MERGED = "merged"

class DetectionSource(enum.Enum):
    """Progress detection source enum."""
    ECOSYSTE_MS_API = "ecosyste_ms_api"
    GITHUB_API = "github_api"

class ProgressTracking(Base):
    """
    Progress Tracking model as specified in MD file:
    progress_tracking table for monitoring PR and commit activity
    """
    __tablename__ = "progress_tracking"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    claim_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("claims.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    pr_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    pr_status: Mapped[Optional[PRStatus]] = mapped_column(
        Enum(PRStatus),
        nullable=True,
        index=True
    )
    commit_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_commit_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    detected_from: Mapped[Optional[DetectionSource]] = mapped_column(
        Enum(DetectionSource),
        nullable=True,
        index=True
    )

    # Relationships - using lazy loading to avoid circular imports
    claim = relationship("Claim", back_populates="progress_tracking", lazy="select")

    def __repr__(self):
        return f"<ProgressTracking(id={self.id}, claim_id={self.claim_id}, pr_number={self.pr_number})>"
