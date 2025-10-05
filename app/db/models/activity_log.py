import enum
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON, Enum
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func
from datetime import datetime, timezone
from typing import Optional

from app.db.database import Base

class ActivityType(enum.Enum):
    """Activity type enum."""
    CLAIM_DETECTED = "CLAIM_DETECTED"
    PROGRESS_NUDGE = "PROGRESS_NUDGE"
    AUTO_RELEASE = "AUTO_RELEASE"
    COMMENT = "COMMENT"
    PROGRESS_UPDATE = "PROGRESS_UPDATE"

class ActivityLog(Base):
    """
    Activity Log model as specified in MD file:
    activity_log table for tracking all system activities
    """
    __tablename__ = "activity_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    claim_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("claims.id", ondelete="CASCADE"), 
        nullable=False,
        index=True
    )
    activity_type: Mapped[ActivityType] = mapped_column(
        Enum(ActivityType),
        nullable=False,
        index=True
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )
    activity_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Relationships - using lazy loading to avoid circular imports
    claim = relationship("Claim", back_populates="activity_logs", lazy="select")

    def __repr__(self):
        return f"<ActivityLog(id={self.id}, type='{self.activity_type.value}', claim_id={self.claim_id})>"
