from sqlalchemy import Column, Integer, String, DateTime, JSON, Index
from datetime import datetime
from . import Base

class QueueJob(Base):
    """
    Queue Jobs model as specified in MD file:
    queue_jobs table for managing background job processing
    """
    __tablename__ = "queue_jobs"

    id = Column(Integer, primary_key=True)
    job_type = Column(String, nullable=False)  # nudge_check/progress_check/auto_release_check/comment_analysis
    payload = Column(JSON)  # issue_id, claim_id, user_data, etc.
    scheduled_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime)
    status = Column(String, default="pending")  # pending/processing/completed/failed/dead_letter
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Indexes for performance as specified in MD file
    __table_args__ = (
        Index('ix_queue_jobs_scheduled_at', 'scheduled_at'),
        Index('ix_queue_jobs_status', 'status'),
    )

    def __repr__(self):
        return f"<QueueJob {self.job_type} - {self.status}>"