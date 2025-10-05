from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from . import Base

class ActivityLog(Base):
    """
    Activity Log model as specified in MD file:
    activity_log table for tracking all system activities
    """
    __tablename__ = "activity_log"

    id = Column(Integer, primary_key=True)
    claim_id = Column(Integer, ForeignKey("claims.id"), nullable=False)
    activity_type = Column(String, nullable=False)  # progress_nudge/auto_release/comment/claim_detected
    description = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)
    activity_metadata = Column(JSON)

    # Relationships
    claim = relationship("Claim", back_populates="activity_logs")

    def __repr__(self):
        return f"<ActivityLog {self.activity_type} for Claim {self.claim_id}>"