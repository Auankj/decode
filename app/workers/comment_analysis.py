"""
Comment Analysis Worker
Implements atomic claim creation with distributed locking as specified in MD file:
- Distributed locking for concurrent issue processing
- Conflict resolution for same/different users
- Transactional operations (INSERT claim + activity_log + schedule job)
"""
from celery import Task
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta
import structlog

from app.workers.celery_app import celery_app, PRIORITY_HIGH
from app.db.models import Claim, ActivityLog, Issue
from app.db.models.claims import ClaimStatus
from app.db.models.activity_log import ActivityType
from app.db.models.queue_jobs import QueueJob, JobType, JobStatus
from app.models import SessionLocal
from app.utils.distributed_lock import distributed_lock, get_issue_lock_key
from app.services.pattern_matcher import pattern_matcher

logger = structlog.get_logger()

class ClaimDetectionTask(Task):
    """
    Base task class with retry and error handling
    """
    autoretry_for = (Exception,)
    retry_kwargs = {"max_retries": 3, "countdown": 60}
    retry_backoff = True

@celery_app.task(
    bind=True, 
    base=ClaimDetectionTask,
    queue="comment_analysis",
    priority=PRIORITY_HIGH
)
def analyze_comment_for_claim(
    self,
    issue_id: int,
    comment_data: dict,
    issue_data: dict,
    repository_config: dict
):
    """
    Comment Analysis Worker as specified in MD file flowchart:
    1. Acquire Lock on Issue
    2. Preprocess Comment  
    3. Run Detection Patterns
    4. Validate Claim
    5. Create Claim Record (atomic transaction)
    """
    
    lock_key = get_issue_lock_key(issue_id)
    lock_value = None
    
    try:
        # Step 1: Acquire distributed lock (from MD file flowchart)
        lock_value = distributed_lock.acquire_lock(
            lock_key=lock_key,
            timeout=300,  # 5 minutes
            max_retries=10
        )
        
        if not lock_value:
            logger.error(f"Failed to acquire lock for issue {issue_id}")
            raise self.retry(countdown=60)
        
        logger.info(f"Processing comment analysis for issue {issue_id}")
        
        # Step 2: Extract comment details
        comment_text = comment_data.get("body", "")
        comment_author = comment_data.get("user", {}).get("login", "")
        comment_id = comment_data.get("id")
        comment_user_id = comment_data.get("user", {}).get("id")
        
        # Step 3: Run pattern matching analysis
        threshold = repository_config.get("claim_detection_threshold", 75)
        analysis_result = pattern_matcher.analyze_comment(
            comment_text=comment_text,
            comment_data=comment_data,
            issue_data=issue_data,
            threshold=threshold
        )
        
        logger.info(f"Pattern analysis result: {analysis_result['final_score']}% confidence")
        
        # Step 4: Check if this qualifies as a claim
        if not analysis_result["is_claim"]:
            # Check for progress updates
            if analysis_result["is_progress_update"]:
                _handle_progress_update(issue_id, comment_user_id, analysis_result)
            
            logger.info(f"Comment does not qualify as claim (score: {analysis_result['final_score']})")
            return {"status": "no_claim", "confidence": analysis_result['final_score']}
        
        # Step 5: Database transaction for claim creation
        db = SessionLocal()
        try:
            result = _create_claim_with_transaction(
                db=db,
                issue_id=issue_id,
                comment_data=comment_data,
                analysis_result=analysis_result,
                repository_config=repository_config
            )
            
            logger.info(f"Successfully created claim for issue {issue_id}")
            return result
            
        except Exception as e:
            db.rollback()
            logger.error(f"Database error during claim creation: {e}")
            raise
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error in comment analysis for issue {issue_id}: {e}")
        raise
    finally:
        # Step 6: Release lock
        if lock_value:
            distributed_lock.release_lock(lock_key, lock_value)

def _create_claim_with_transaction(
    db: Session, 
    issue_id: int, 
    comment_data: dict, 
    analysis_result: dict,
    repository_config: dict
) -> dict:
    """
    Atomic transactional operations as specified in MD file:
    INSERT claim record + INSERT activity_log + SCHEDULE nudge job
    """
    
    comment_user_id = comment_data.get("user", {}).get("id")
    comment_username = comment_data.get("user", {}).get("login", "")
    
    # Check for existing claims (conflict resolution from MD file)
    existing_claim = db.query(Claim).filter(
        Claim.issue_id == issue_id,
        Claim.status == ClaimStatus.ACTIVE
    ).first()
    
    if existing_claim:
        if existing_claim.github_user_id == comment_user_id:
            # Same user updating metadata (from MD file)
            existing_claim.claim_text = comment_data.get("body", "")
            existing_claim.confidence_score = analysis_result["final_score"]
            existing_claim.context_metadata = analysis_result["analysis_metadata"]
            existing_claim.last_activity_timestamp = datetime.utcnow()
            
            db.commit()
            return {"status": "claim_updated", "claim_id": existing_claim.id}
        else:
            # Different user - conflict resolution required (from MD file)
            logger.warning(f"Conflict: Issue {issue_id} already claimed by {existing_claim.github_username}")
            return {"status": "conflict", "existing_claimer": existing_claim.github_username}
    
    # START TRANSACTION (from MD file flowchart)
    try:
        # INSERT claim record
        new_claim = Claim(
            issue_id=issue_id,
            repository_id=repository_config.get("repository_id"),
            github_user_id=comment_user_id,
            github_username=comment_username,
            claim_comment_id=comment_data.get("id"),
            claim_text=comment_data.get("body", ""),
            claim_timestamp=datetime.utcnow(),
            status=ClaimStatus.ACTIVE,
            last_activity_timestamp=datetime.utcnow(),
            confidence_score=analysis_result["final_score"],
            context_metadata=analysis_result.get("analysis_metadata", {})
        )
        
        db.add(new_claim)
        db.flush()  # Get the claim ID
        
        # Convert analysis_result to JSON-serializable format
        json_safe_metadata = {
            "final_score": analysis_result.get("final_score", 0),
            "is_claim": analysis_result.get("is_claim", False),
            "is_progress_update": analysis_result.get("is_progress_update", False),
            "analysis_metadata": analysis_result.get("analysis_metadata", {})
        }
        
        # INSERT activity_log
        activity_log = ActivityLog(
            claim_id=new_claim.id,
            activity_type=ActivityType.CLAIM_DETECTED,
            description=f"Claim detected with {analysis_result['final_score']}% confidence",
            timestamp=datetime.utcnow(),
            activity_metadata=json_safe_metadata
        )
        
        db.add(activity_log)
        
        # SCHEDULE nudge job
        grace_period_days = repository_config.get("grace_period_days", 7)
        nudge_time = datetime.utcnow() + timedelta(days=grace_period_days)
        
        nudge_job = QueueJob(
            job_type=JobType.NUDGE_CHECK,
            payload={
                "claim_id": new_claim.id,
                "issue_id": issue_id,
                "user_id": comment_user_id,
                "username": comment_username
            },
            scheduled_at=nudge_time,
            status=JobStatus.PENDING
        )
        
        db.add(nudge_job)
        
        # COMMIT TRANSACTION
        db.commit()
        
        return {
            "status": "claim_created",
            "claim_id": new_claim.id,
            "confidence": analysis_result["final_score"],
            "nudge_scheduled_at": nudge_time.isoformat()
        }
        
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Integrity error during claim creation: {e}")
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error during claim creation: {e}")
        raise

def _handle_progress_update(issue_id: int, user_id: int, analysis_result: dict):
    """
    Handle progress updates to reset timers (from MD file)
    """
    from app.workers.progress_check import reset_claim_timers
    
    # Schedule progress check to reset timers
    reset_claim_timers.delay(
        issue_id=issue_id,
        user_id=user_id,
        progress_data=analysis_result
    )