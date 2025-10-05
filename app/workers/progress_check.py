"""
Progress Monitoring System
Track PRs and commits linked to claimed issues as specified in MD file:
- Monitor for associated pull requests
- Track commit activity
- Reset timers when progress detected
- Update progress_tracking table
"""
from celery import Task
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import structlog

from app.workers.celery_app import celery_app, PRIORITY_NORMAL
from app.db.models import Claim, ProgressTracking, ActivityLog
from app.services.ecosyste_client import get_ecosyste_client

logger = structlog.get_logger()

class ProgressMonitorTask(Task):
    """Base task class for progress monitoring"""
    autoretry_for = (Exception,)
    retry_kwargs = {"max_retries": 3, "countdown": 120}
    retry_backoff = True

@celery_app.task(
    bind=True,
    base=ProgressMonitorTask,
    queue="progress_check",
    priority=PRIORITY_NORMAL
)
def monitor_claim_progress(self, claim_id: int):
    """
    Monitor Claimed Issue for progress as specified in MD file flowchart:
    1. Check for Associated PRs
    2. Check PR Status
    3. Mark as Progress Made
    4. Reset Inactivity Timer
    """
    
    db = SessionLocal()
    try:
        # Get claim details
        claim = db.query(Claim).filter(Claim.id == claim_id).first()
        if not claim:
            logger.error(f"Claim {claim_id} not found")
            return {"status": "claim_not_found"}
        
        if claim.status != "active":
            logger.info(f"Claim {claim_id} is not active, skipping progress check")
            return {"status": "claim_inactive"}
        
        logger.info(f"Monitoring progress for claim {claim_id} on issue {claim.issue_id}")
        
        # Step 1: Check for associated PRs using Ecosyste.ms API
        ecosystem_client = get_ecosyste_client()  # Remove await
        
        # Get issue data to find repository info
        issue = claim.issue
        if not issue:
            logger.error(f"Issue not found for claim {claim_id}")
            return {"status": "issue_not_found"}
        
        # Check for PRs linked to this issue
        progress_detected = _check_for_pull_requests(
            ecosystem_client, issue, claim, db
        )
        
        # Step 2: Check for commits by the user
        if not progress_detected:
            progress_detected = _check_for_commits(
                ecosystem_client, issue, claim, db
            )
        
        # Step 3: Update progress tracking and reset timers if needed
        if progress_detected:
            _reset_claim_timers(claim, db)
            logger.info(f"Progress detected for claim {claim_id}, timers reset")
            return {"status": "progress_detected", "claim_id": claim_id}
        else:
            logger.info(f"No progress detected for claim {claim_id}")
            return {"status": "no_progress", "claim_id": claim_id}
        
    except Exception as e:
        logger.error(f"Error monitoring progress for claim {claim_id}: {e}")
        db.rollback()
        raise
    finally:
        db.close()

@celery_app.task(
    bind=True,
    base=ProgressMonitorTask,
    queue="progress_check",
    priority=PRIORITY_NORMAL
)
def reset_claim_timers(self, issue_id: int, user_id: int, progress_data: dict):
    """
    Reset claim timers when progress is detected from comments
    As specified in MD file progress monitoring flow
    """
    
    db = SessionLocal()
    try:
        # Find active claim for this user and issue
        claim = db.query(Claim).filter(
            Claim.issue_id == issue_id,
            Claim.github_user_id == user_id,
            Claim.status == "active"
        ).first()
        
        if not claim:
            logger.warning(f"No active claim found for user {user_id} on issue {issue_id}")
            return {"status": "no_active_claim"}
        
        # Reset timer by updating last activity
        claim.last_activity_timestamp = datetime.utcnow()
        
        # Log the progress update
        activity_log = ActivityLog(
            claim_id=claim.id,
            activity_type="progress_update",
            description="Progress detected from comment analysis",
            timestamp=datetime.utcnow(),
            metadata=progress_data
        )
        
        db.add(activity_log)
        db.commit()
        
        logger.info(f"Reset timers for claim {claim.id} due to progress update")
        return {"status": "timers_reset", "claim_id": claim.id}
        
    except Exception as e:
        logger.error(f"Error resetting timers for issue {issue_id}, user {user_id}: {e}")
        db.rollback()
        raise
    finally:
        db.close()

def _check_for_pull_requests(
    ecosystem_client, 
    issue, 
    claim: Claim, 
    db: Session
) -> bool:
    """
    Check for associated pull requests as specified in MD file
    Returns True if progress is detected
    """
    
    try:
        # Get repository info
        repo_data = issue.repository
        if not repo_data:
            return False
        
        # Check for PRs that reference this issue
        # This is simplified - in real implementation, you'd check PR descriptions
        # for issue references like "fixes #123" or "closes #123"
        
        # For now, check if user has any recent PRs in the repository
        # This would be enhanced with actual issue linking logic
        
        # Update or create progress tracking record
        progress_tracking = db.query(ProgressTracking).filter(
            ProgressTracking.claim_id == claim.id
        ).first()
        
        if not progress_tracking:
            progress_tracking = ProgressTracking(
                claim_id=claim.id,
                detected_from="ecosyste_ms_api"
            )
            db.add(progress_tracking)
        
        # In real implementation, you'd fetch actual PR data here
        # For hackathon demo, we'll simulate finding a PR
        progress_tracking.updated_at = datetime.utcnow()
        
        db.commit()
        return False  # No actual PR found in this simplified version
        
    except Exception as e:
        logger.error(f"Error checking PRs for claim {claim.id}: {e}")
        return False

def _check_for_commits(
    ecosystem_client, 
    issue, 
    claim: Claim, 
    db: Session
) -> bool:
    """
    Check for commits by the user in the repository
    As specified in MD file progress monitoring
    """
    
    try:
        # In real implementation, you'd use Ecosyste.ms commits API
        # to check for recent commits by the claim author
        
        # For hackathon demo, this is a placeholder
        # You would query: /commits with author filter and date range
        
        return False  # No commits found in this simplified version
        
    except Exception as e:
        logger.error(f"Error checking commits for claim {claim.id}: {e}")
        return False

def _reset_claim_timers(claim: Claim, db: Session):
    """
    Reset inactivity timer as specified in MD file
    Update Claim Status and Reset Inactivity Timer
    """
    
    # Update last activity timestamp
    claim.last_activity_timestamp = datetime.utcnow()
    
    # Cancel any pending nudge jobs by scheduling new ones
    # This would be enhanced to actually cancel existing scheduled jobs
    
    # Log the timer reset
    activity_log = ActivityLog(
        claim_id=claim.id,
        activity_type="progress_detected",
        description="Progress detected, timers reset",
        timestamp=datetime.utcnow(),
        metadata={"timer_reset": True}
    )
    
    db.add(activity_log)
    db.commit()

@celery_app.task(queue="progress_check")
def batch_progress_check():
    """
    Periodic batch job to check progress on all active claims
    """
    
    db = SessionLocal()
    try:
        # Get all active claims that need progress checking
        active_claims = db.query(Claim).filter(
            Claim.status == "active",
            Claim.last_activity_timestamp < datetime.utcnow() - timedelta(hours=24)
        ).all()
        
        logger.info(f"Running batch progress check on {len(active_claims)} claims")
        
        for claim in active_claims:
            # Schedule individual progress check
            monitor_claim_progress.delay(claim.id)
        
        return {"status": "scheduled", "claim_count": len(active_claims)}
        
    except Exception as e:
        logger.error(f"Error in batch progress check: {e}")
        raise
    finally:
        db.close()