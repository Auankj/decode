from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from . import Base

class Claim(Base):
    """
    Claims model as specified in MD file:
    claims table with confidence scoring and context metadata
    """
    __tablename__ = "claims"

    id = Column(Integer, primary_key=True)
    issue_id = Column(Integer, ForeignKey("issues.id"), nullable=False)
    github_user_id = Column(Integer, nullable=False)
    github_username = Column(String, nullable=False)
    claim_comment_id = Column(Integer)
    claim_text = Column(Text)
    claim_timestamp = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="active")  # active/inactive/completed/released
    first_nudge_sent_at = Column(DateTime)
    last_activity_timestamp = Column(DateTime, default=datetime.utcnow)
    auto_release_timestamp = Column(DateTime)
    release_reason = Column(String)
    confidence_score = Column(Integer)  # 0-100, calculated during claim detection
    context_metadata = Column(JSON)  # reply context, user assignment status
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    issue = relationship("Issue", back_populates="claims")
    activity_logs = relationship("ActivityLog", back_populates="claim")
    progress_tracking = relationship("ProgressTracking", back_populates="claim", uselist=False)

    def __repr__(self):
        return f"<Claim by {self.github_username} on Issue #{self.issue.github_issue_number}>"