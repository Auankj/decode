import enum
from sqlalchemy import Column, Integer, BigInteger, String, DateTime, JSON, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func
from datetime import datetime, timezone
from typing import Optional

from app.db.database import Base

class IssueStatus(enum.Enum):
    """Status enum for issues."""
    OPEN = "open"
    CLOSED = "closed"

class Issue(Base):
    """
    Issue model as specified in MD file:
    issues table with GitHub issue data
    """
    __tablename__ = "issues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    repository_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    github_repo_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    github_issue_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    github_issue_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[IssueStatus] = mapped_column(
        Enum(IssueStatus),
        default=IssueStatus.OPEN,
        nullable=False,
        index=True
    )
    
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
    github_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # raw GitHub issue data

    # Relationships - using lazy loading to avoid circular imports
    repository = relationship("Repository", back_populates="issues", lazy="select")
    claims = relationship("Claim", back_populates="issue", cascade="all, delete-orphan", lazy="select")

    def __repr__(self):
        return f"<Issue(id={self.id}, number=#{self.github_issue_number}, title='{self.title[:50]}...')>"
