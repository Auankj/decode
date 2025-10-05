"""
Complete Progress Check Implementation with Real Ecosyste.ms API Integration
As specified in MD file: Full PR and commit tracking
"""

import asyncio
from typing import Dict, Any, List
from datetime import datetime, timezone, timedelta
from app.core.celery_app import celery_app
from app.core.logging import get_logger
from app.models import SessionLocal, Claim, ProgressTracking, ActivityLog, Issue, Repository
from app.services.ecosyste_client import get_ecosyste_client

logger = get_logger(__name__)


@celery_app.task(bind=True, max_retries=3)
def check_progress_task(self, claim_id: int):
    """
    Complete progress check implementation as specified in MD file:
    1. Check for PRs that reference the issues
    2. Check for commits that reference the issues  
    3. Update progress tracking in database
    4. Reset nudge timers if progress is detected
    """
    try:
        logger.info(f"Checking progress for claim {claim_id}")
        
        # Run the async progress check
        result = asyncio.run(_check_claim_progress_async(claim_id))
        
        if result["progress_detected"]:
            logger.info(f"Progress detected for claim {claim_id}: {result['progress_type']}")
        else:
            logger.info(f"No progress detected for claim {claim_id}")
        
        return result
        
    except Exception as exc:
        logger.error(f"Progress check failed for claim {claim_id}: {exc}")
        raise self.retry(countdown=60, exc=exc)


async def _check_claim_progress_async(claim_id: int) -> Dict[str, Any]:
    """Async implementation of progress checking"""
    db = SessionLocal()
    try:
        # Get claim and related data
        claim = db.query(Claim).filter(Claim.id == claim_id).first()
        if not claim:
            return {"status": "error", "message": "Claim not found", "progress_detected": False}
        
        if claim.status != "active":
            return {"status": "skipped", "message": "Claim not active", "progress_detected": False}
        
        issue = claim.issue
        if not issue or not issue.repository:
            return {"status": "error", "message": "Issue or repository not found", "progress_detected": False}
        
        repo = issue.repository
        
        # Get Ecosyste.ms client
        ecosyste_client = await get_ecosyste_client()
        
        progress_detected = False
        progress_details = []
        
        # Check for PRs that reference this issue
        logger.info(f"Checking PRs for issue #{issue.github_issue_number} in {repo.owner}/{repo.name}")
        referenced_prs = await ecosyste_client.check_issue_pr_references(
            owner=repo.owner,
            name=repo.name,
            issue_number=issue.github_issue_number,
            username=claim.github_username,
            since=claim.claim_timestamp
        )
        
        if referenced_prs:
            progress_detected = True
            progress_details.append({
                "type": "pull_request",
                "count": len(referenced_prs),
                "details": [{
                    "pr_number": pr.get("number"),
                    "pr_title": pr.get("title"),
                    "pr_state": pr.get("state"),
                    "created_at": pr.get("created_at")
                } for pr in referenced_prs[:5]]  # Limit to first 5 PRs
            })
        
        # Check for commits by the user since claim
        logger.info(f"Checking commits by {claim.github_username} in {repo.owner}/{repo.name}")
        user_commits = await ecosyste_client.get_user_commits(
            owner=repo.owner,
            repo=repo.name,
            username=claim.github_username,
            since=claim.claim_timestamp
        )
        
        if user_commits:
            progress_detected = True
            progress_details.append({
                "type": "commits",
                "count": len(user_commits),
                "details": [{
                    "sha": commit.get("sha", "")[:8],  # Short SHA
                    "message": commit.get("message", "")[:100],  # First 100 chars
                    "date": commit.get("commit", {}).get("author", {}).get("date")
                } for commit in user_commits[:5]]  # Limit to first 5 commits
            })
        
        # Update progress tracking record
        progress_tracking = db.query(ProgressTracking).filter(
            ProgressTracking.claim_id == claim_id
        ).first()
        
        if not progress_tracking:
            progress_tracking = ProgressTracking(
                claim_id=claim_id,
                detected_from="ecosyste_ms_api"
            )
            db.add(progress_tracking)
        
        # Update progress tracking with findings
        if referenced_prs:
            progress_tracking.pr_number = referenced_prs[0].get("number")
            progress_tracking.pr_status = referenced_prs[0].get("state")
        
        if user_commits:
            progress_tracking.commit_count = len(user_commits)
            progress_tracking.last_commit_date = datetime.fromisoformat(
                user_commits[0].get("commit", {}).get("author", {}).get("date", datetime.now().isoformat())
            )
        
        progress_tracking.updated_at = datetime.now(timezone.utc)
        
        # If progress detected, reset claim timers
        if progress_detected:
            claim.last_activity_timestamp = datetime.now(timezone.utc)
            
            # Log the progress detection
            activity_log = ActivityLog(
                claim_id=claim_id,
                activity_type="progress_detected",
                description=f"Progress detected: {', '.join([d['type'] for d in progress_details])}",
                timestamp=datetime.now(timezone.utc),
                metadata={
                    "progress_details": progress_details,
                    "detection_method": "ecosyste_ms_api"
                }
            )
            db.add(activity_log)
        
        db.commit()
        
        return {
            "status": "completed",
            "progress_detected": progress_detected,
            "progress_type": [d["type"] for d in progress_details] if progress_details else [],
            "claim_id": claim_id,
            "details": progress_details
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error in progress check for claim {claim_id}: {e}")
        raise
    finally:
        db.close()


@celery_app.task
def batch_progress_check(claim_ids: List[int]):
    """
    Batch check progress for multiple claims.
    """
    results = []
    for claim_id in claim_ids:
        result = check_progress_task.delay(claim_id)
        results.append(result.id)
    
    return {
        "status": "batch_queued",
        "task_count": len(claim_ids),
        "task_ids": results
    }


@celery_app.task
def update_progress_task(claim_id: int):
    """
    Force update progress tracking for a specific claim
    Used by API endpoints for manual progress updates
    """
    return check_progress_task(claim_id)
