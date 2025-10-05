import enum
from sqlalchemy import Column, Integer, BigInteger, String, DateTime, ForeignKey, Text, JSON, Enum
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func
from datetime import datetime, timezone
from typing import Optional

from app.db.database import Base

class ClaimStatus(enum.Enum):
    """Status enum for claims."""
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    COMPLETED = "COMPLETED"
    RELEASED = "RELEASED"
    EXPIRED = "EXPIRED"

class Claim(Base):
    """
    Claims model as specified in MD file:
    claims table with confidence scoring and context metadata
    """
    __tablename__ = "claims"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    issue_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("issues.id", ondelete="CASCADE"), 
        nullable=False,
        index=True
    )
    repository_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    github_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    github_username: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    claim_comment_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    claim_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    claim_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        nullable=False,
        index=True
    )
    status: Mapped[ClaimStatus] = mapped_column(
        Enum(ClaimStatus),
        default=ClaimStatus.ACTIVE,
        nullable=False,
        index=True
    )
    first_nudge_sent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), 
        nullable=True
    )
    last_activity_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    auto_release_timestamp: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    release_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    confidence_score: Mapped[int] = mapped_column(Integer, nullable=False)  # 0-100, calculated during claim detection
    context_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # reply context, user assignment status
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    # Relationships - using lazy loading to avoid circular imports
    issue = relationship("Issue", back_populates="claims", lazy="select")
    repository = relationship("Repository", back_populates="claims", lazy="select")
    user = relationship("User", back_populates="claims", lazy="select")
    activity_logs = relationship("ActivityLog", back_populates="claim", cascade="all, delete-orphan", lazy="select")
    progress_tracking = relationship("ProgressTracking", back_populates="claim", uselist=False, cascade="all, delete-orphan", lazy="select")

    def __repr__(self):
        return f"<Claim(id={self.id}, user='{self.github_username}', status='{self.status.value}')>"
