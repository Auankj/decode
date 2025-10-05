from sqlalchemy import Column, Integer, BigInteger, String, Boolean, JSON, DateTime, ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func
from datetime import datetime, timezone
from typing import Optional, List

from app.db.database import Base

class Repository(Base):
    """
    Repository model as specified in MD file:
    repositories table with monitoring configuration
    """
    __tablename__ = "repositories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    github_repo_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    owner_id: Mapped[Optional[int]] = mapped_column(
        Integer, 
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    owner_name: Mapped[str] = mapped_column(String(255), nullable=False)  # GitHub owner name
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(512), nullable=False)  # owner/repo
    url: Mapped[str] = mapped_column(String(512), nullable=False)
    is_monitored: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    grace_period_days: Mapped[int] = mapped_column(Integer, default=7, nullable=False)
    nudge_count: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    notification_settings: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    claim_detection_threshold: Mapped[int] = mapped_column(Integer, default=75, nullable=False)  # minimum confidence score
    
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
    owner = relationship("User", back_populates="repositories", lazy="select")
    issues = relationship("Issue", back_populates="repository", cascade="all, delete-orphan", lazy="select")
    claims = relationship("Claim", back_populates="repository", cascade="all, delete-orphan", lazy="select")

    def __repr__(self):
        return f"<Repository(id={self.id}, full_name='{self.full_name}', monitored={self.is_monitored})>"
