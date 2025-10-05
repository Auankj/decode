from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from . import Base

class Issue(Base):
    """
    Issue model as specified in MD file:
    issues table with GitHub issue data
    """
    __tablename__ = "issues"

    id = Column(Integer, primary_key=True)
    github_repo_id = Column(Integer, ForeignKey("repositories.github_repo_id"), nullable=False)
    github_issue_number = Column(Integer, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text)
    status = Column(String, default="open")  # open/closed
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    github_data = Column(JSON)  # raw GitHub issue data

    # Relationships
    repository = relationship("Repository", back_populates="issues")
    claims = relationship("Claim", back_populates="issue")

    def __repr__(self):
        return f"<Issue #{self.github_issue_number}: {self.title}>"