"""
Nudge Notification System
Implements notification and auto-release flow as specified in MD file:
- Send nudge notifications after grace period
- Auto-release after max nudges
- GitHub API integration for assignments/comments  
"""
from celery import Task
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import structlog
import os

from app.workers.celery_app import celery_app, PRIORITY_HIGH
from app.db.models import Claim, ActivityLog
from app.models.queue_jobs import QueueJob
from app.services.notification_service import send_nudge_email, post_github_comment

logger = structlog.get_logger()

class NudgeTask(Task):
    """Base task class for nudge notifications"""
    autoretry_for = (Exception,)
    retry_kwargs = {"max_retries": 3, "countdown": 300}  # 5 minutes
    retry_backoff = True

@celery_app.task(
    bind=True,
    base=NudgeTask,
    queue="nudge_check",
    priority=PRIORITY_HIGH
)
def process_nudge_check(self, claim_id: int):
    """
    Nudge notification flow as specified in MD file:
    Timer Expires → Check Issue Activity → Send Nudge or Auto-Release
    """
    
    db = SessionLocal()
    try:
        # Get claim details
        claim = db.query(Claim).filter(Claim.id == claim_id).first()
        if not claim:
            logger.error(f"Claim {claim_id} not found for nudge check")
            return {"status": "claim_not_found"}
        
        if claim.status != "active":
            logger.info(f"Claim {claim_id} is not active, skipping nudge")
            return {"status": "claim_inactive"}
        
        logger.info(f"Processing nudge check for claim {claim_id}")
        
        # Check issue activity (from MD file flowchart)
        has_recent_activity = _check_recent_activity(claim)
        
        if has_recent_activity:
            # Reset Timer (from MD file)
            _reset_nudge_timer(claim, db)
            logger.info(f"Recent activity found, reset timer for claim {claim_id}")
            return {"status": "timer_reset", "claim_id": claim_id}
        
        # No recent activity - proceed with nudge flow
        nudge_count = _get_nudge_count(claim, db)
        max_nudges = _get_max_nudges(claim)
        
        if nudge_count < max_nudges:
            # Send Nudge Notification (from MD file)
            result = _send_nudge_notification(claim, db)
            return result
        else:
            # Mark for Auto-Release (from MD file)
            result = _execute_auto_release(claim, db)
            return result
        
    except Exception as e:
        logger.error(f"Error in nudge check for claim {claim_id}: {e}")
        db.rollback()
        raise
    finally:
        db.close()

def _check_recent_activity(claim: Claim) -> bool:
    """
    Check Issue Activity as specified in MD file flowchart
    Returns True if recent activity found
    """
    
    # Check if last activity was recent (within grace period)
    grace_period = timedelta(days=7)  # Default from config
    cutoff_time = datetime.utcnow() - grace_period
    
    if claim.last_activity_timestamp > cutoff_time:
        return True
    
    # Additional checks could include:
    # - Recent comments on the issue
    # - Recent commits by the user
    # - Recent PR updates
    
    return False

def _get_nudge_count(claim: Claim, db: Session) -> int:
    """Get current nudge count for the claim"""
    
    nudge_count = db.query(ActivityLog).filter(
        ActivityLog.claim_id == claim.id,
        ActivityLog.activity_type == "progress_nudge"
    ).count()
    
    return nudge_count

def _get_max_nudges(claim: Claim) -> int:
    """Get max nudges from repository configuration"""
    
    if claim.issue and claim.issue.repository:
        return claim.issue.repository.nudge_count
    
    return int(os.getenv("DEFAULT_NUDGE_COUNT", "2"))

def _reset_nudge_timer(claim: Claim, db: Session):
    """
    Reset Timer as specified in MD file flowchart
    """
    
    # Update last activity timestamp
    claim.last_activity_timestamp = datetime.utcnow()
    
    # Schedule next nudge check
    grace_period_days = 7  # From repository config
    next_check = datetime.utcnow() + timedelta(days=grace_period_days)
    
    next_nudge_job = QueueJob(
        job_type="nudge_check",
        payload={
            "claim_id": claim.id,
            "issue_id": claim.issue_id,
            "user_id": claim.github_user_id
        },
        scheduled_at=next_check,
        status="pending"
    )
    
    db.add(next_nudge_job)
    
    # Log the timer reset
    activity_log = ActivityLog(
        claim_id=claim.id,
        activity_type="timer_reset",
        description="Nudge timer reset due to recent activity",
        timestamp=datetime.utcnow()
    )
    
    db.add(activity_log)
    db.commit()

def _send_nudge_notification(claim: Claim, db: Session) -> dict:
    """
    Send Nudge Notification as specified in MD file flowchart
    """
    
    try:
        # Record first nudge timestamp if this is the first one
        if not claim.first_nudge_sent_at:
            claim.first_nudge_sent_at = datetime.utcnow()
        
        # Send email notification (if configured)
        email_sent = send_nudge_email(claim)  # Sync call for Celery worker
        
        # Post GitHub comment (if configured)
        comment_posted = post_github_comment(claim)  # Sync call for Celery worker
        
        # Update Notification Log (from MD file)
        activity_log = ActivityLog(
            claim_id=claim.id,
            activity_type="progress_nudge",
            description=f"Nudge sent to {claim.github_username}",
            timestamp=datetime.utcnow(),
            activity_metadata={
                "email_sent": email_sent,
                "comment_posted": comment_posted,
                "nudge_count": _get_nudge_count(claim, db) + 1
            }
        )
        
        db.add(activity_log)
        
        # Schedule next nudge check
        grace_period_days = 7  # From repository config  
        next_check = datetime.utcnow() + timedelta(days=grace_period_days)
        
        next_nudge_job = QueueJob(
            job_type="nudge_check",
            payload={
                "claim_id": claim.id,
                "issue_id": claim.issue_id,
                "user_id": claim.github_user_id
            },
            scheduled_at=next_check,
            status="pending"
        )
        
        db.add(next_nudge_job)
        db.commit()
        
        logger.info(f"Nudge sent for claim {claim.id}, next check at {next_check}")
        return {
            "status": "nudge_sent",
            "claim_id": claim.id,
            "next_check": next_check.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error sending nudge for claim {claim.id}: {e}")
        db.rollback()
        raise

def _execute_auto_release(claim: Claim, db: Session) -> dict:
    """
    Execute Auto-Release as specified in MD file flowchart
    """
    
    try:
        # Mark for Auto-Release
        claim.status = "released"
        claim.auto_release_timestamp = datetime.utcnow()
        claim.release_reason = "auto_released_after_max_nudges"
        
        # Log the auto-release
        activity_log = ActivityLog(
            claim_id=claim.id,
            activity_type="auto_release",
            description=f"Claim auto-released after maximum nudges",
            timestamp=datetime.utcnow(),
            activity_metadata={
                "release_reason": "max_nudges_exceeded",
                "nudge_count": _get_nudge_count(claim, db)
            }
        )
        
        db.add(activity_log)
        
        # Remove GitHub assignment (if exists)
        from app.services.github_service import remove_issue_assignee
        remove_issue_assignee(claim)  # Sync call for Celery worker
        
        # Notify Maintainer (from MD file)
        _notify_maintainer_of_release(claim)  # Sync call
        
        db.commit()
        
        logger.info(f"Claim {claim.id} auto-released after max nudges")
        return {
            "status": "auto_released",
            "claim_id": claim.id,
            "release_timestamp": claim.auto_release_timestamp.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error auto-releasing claim {claim.id}: {e}")
        db.rollback()
        raise

def _notify_maintainer_of_release(claim: Claim):
    """
    Notify Maintainer as specified in MD file flowchart
    """
    
    try:
        # Post comment on issue notifying of auto-release
        from app.services.github_service import post_maintainer_notification
        
        post_maintainer_notification(
            issue=claim.issue,
            message=f"🤖 This issue has been automatically unassigned from @{claim.github_username} "
                   f"due to inactivity. The issue is now available for others to work on."
        )  # Sync call for Celery worker
        
        logger.info(f"Maintainer notified of auto-release for claim {claim.id}")
        
    except Exception as e:
        logger.error(f"Error notifying maintainer of auto-release for claim {claim.id}: {e}")

@celery_app.task(queue="nudge_check")
def batch_nudge_check():
    """
    Periodic batch job to process all pending nudge checks
    """
    
    db = SessionLocal()
    try:
        # Get all pending nudge jobs that are due
        due_jobs = db.query(QueueJob).filter(
            QueueJob.job_type == "nudge_check",
            QueueJob.status == "pending",
            QueueJob.scheduled_at <= datetime.utcnow()
        ).all()
        
        logger.info(f"Processing {len(due_jobs)} due nudge jobs")
        
        for job in due_jobs:
            # Mark job as processing
            job.status = "processing"
            job.processed_at = datetime.utcnow()
            db.commit()
            
            # Schedule the actual nudge check
            claim_id = job.payload.get("claim_id")
            if claim_id:
                process_nudge_check.delay(claim_id)
            
            # Mark job as completed
            job.status = "completed"
            db.commit()
        
        return {"status": "processed", "job_count": len(due_jobs)}
        
    except Exception as e:
        logger.error(f"Error in batch nudge check: {e}")
        raise
    finally:
        db.close()