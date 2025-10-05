"""
Database models for Cookie Licking Detector.

This module imports all database models in the correct order to ensure
proper relationship resolution without circular import issues.
"""

# Import Base from the proper database module
from ..database import Base

# Import all models in dependency order to ensure proper relationship setup
# 1. First import models with no relationships
from .user import User, APIKey, UserRole, UserSession, LoginAttempt, PasswordReset, APIScope

# 2. Import models that reference users
from .repositories import Repository

# 3. Import models that reference repositories
from .issues import Issue, IssueStatus

# 4. Import models that reference both users and repositories/issues
from .claims import Claim, ClaimStatus

# 5. Import models that reference claims
from .activity_log import ActivityLog, ActivityType
from .progress_tracking import ProgressTracking, PRStatus, DetectionSource

# 6. Import standalone models
from .queue_jobs import QueueJob, JobType, JobStatus

# Export all models and enums
__all__ = [
    "Base",
    # User models
    "User", "APIKey", "UserRole", "UserSession", "LoginAttempt", "PasswordReset", "APIScope",
    # Repository models
    "Repository",
    # Issue models
    "Issue", "IssueStatus",
    # Claim models
    "Claim", "ClaimStatus",
    # Activity models
    "ActivityLog", "ActivityType",
    # Progress tracking models
    "ProgressTracking", "PRStatus", "DetectionSource",
    # Queue models
    "QueueJob", "JobType", "JobStatus"
]
