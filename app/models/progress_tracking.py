from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from . import Base

class ProgressTracking(Base):
    """
    Progress Tracking model as specified in MD file:
    progress_tracking table for monitoring PR and commit activity
    """
    __tablename__ = "progress_tracking"

    id = Column(Integer, primary_key=True)
    claim_id = Column(Integer, ForeignKey("claims.id"), nullable=False)
    pr_number = Column(Integer)
    pr_status = Column(String)  # open/closed/merged
    commit_count = Column(Integer, default=0)
    last_commit_date = Column(DateTime)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    detected_from = Column(String)  # ecosyste_ms_api/github_api

    # Relationships
    claim = relationship("Claim", back_populates="progress_tracking")

    def __repr__(self):
        return f"<ProgressTracking for Claim {self.claim_id}>"