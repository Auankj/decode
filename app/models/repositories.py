from sqlalchemy import Column, Integer, String, Boolean, JSON, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from . import Base

class Repository(Base):
    """
    Repository model as specified in MD file:
    repositories table with monitoring configuration
    """
    __tablename__ = "repositories"

    id = Column(Integer, primary_key=True)
    github_repo_id = Column(Integer, unique=True, nullable=False)
    owner = Column(String, nullable=False)
    name = Column(String, nullable=False)
    url = Column(String, nullable=False)
    is_monitored = Column(Boolean, default=True)
    grace_period_days = Column(Integer, default=7)
    nudge_count = Column(Integer, default=2)
    notification_settings = Column(JSON)
    claim_detection_threshold = Column(Integer, default=75)  # minimum confidence score
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    issues = relationship("Issue", back_populates="repository")

    def __repr__(self):
        return f"<Repository {self.owner}/{self.name}>"