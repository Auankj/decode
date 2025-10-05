"""
Progress Tracking Endpoints
As specified in MD file API Design section:
- GET /api/progress/{claim_id}
- POST /api/progress/{claim_id}/update
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from pydantic import BaseModel
from datetime import datetime

from app.db.database import get_async_session
from app.db.models import Claim, ProgressTracking, Issue, Repository, ActivityLog, ActivityType
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()

# Pydantic models
class ProgressResponse(BaseModel):
    id: int
    claim_id: int
    pr_number: Optional[int]
    pr_status: Optional[str]
    commit_count: int
    last_commit_date: Optional[datetime]
    updated_at: datetime
    detected_from: str
    
    class Config:
        from_attributes = True

class ProgressDetail(BaseModel):
    claim_id: int
    progress_tracking: Optional[ProgressResponse]
    claim_info: dict
    issue_info: dict
    recent_activity: list

@router.get("/progress/{claim_id}", response_model=ProgressDetail)
async def get_progress_details(
    claim_id: int,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get progress details for a claim
    As specified in MD file: GET /api/progress/{claim_id}
    Includes PR status, commit activity
    """
    
    # Get the claim
    stmt = select(Claim).where(Claim.id == claim_id)
    result = await db.execute(stmt)
    claim = result.scalar_one_or_none()
    
    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Claim {claim_id} not found"
        )
    
    # Get progress tracking data
    progress_stmt = select(ProgressTracking).where(
        ProgressTracking.claim_id == claim_id
    )
    progress_result = await db.execute(progress_stmt)
    progress_tracking = progress_result.scalar_one_or_none()
    
    # Get recent activity from activity log
    activities_stmt = select(ActivityLog).where(
        ActivityLog.claim_id == claim_id
    ).order_by(ActivityLog.timestamp.desc()).limit(10)
    
    activities_result = await db.execute(activities_stmt)
    recent_activities = activities_result.scalars().all()
    
    activity_list = [
        {
            "id": activity.id,
            "type": activity.activity_type,
            "description": activity.description,
            "timestamp": activity.timestamp.isoformat(),
            "metadata": activity.activity_metadata
        }
        for activity in recent_activities
    ]
    
    return ProgressDetail(
        claim_id=claim_id,
        progress_tracking=progress_tracking,
        claim_info={
            "id": claim.id,
            "username": claim.github_username,
            "status": claim.status,
            "claim_timestamp": claim.claim_timestamp.isoformat(),
            "confidence_score": claim.confidence_score,
            "last_activity": claim.last_activity_timestamp.isoformat()
        },
        issue_info={
            "id": claim.issue.id,
            "number": claim.issue.github_issue_number,
            "title": claim.issue.title,
            "status": claim.issue.status,
            "repository": f"{claim.issue.repository.owner}/{claim.issue.repository.name}" if claim.issue.repository else None
        } if claim.issue else {},
        recent_activity=activity_list
    )

@router.post("/progress/{claim_id}/update")
async def force_update_progress(
    claim_id: int,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Force update progress tracking
    As specified in MD file: POST /api/progress/{claim_id}/update
    """
    
    # Verify claim exists
    stmt = select(Claim).where(Claim.id == claim_id)
    result = await db.execute(stmt)
    claim = result.scalar_one_or_none()
    
    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Claim {claim_id} not found"
        )
    
    try:
        # Trigger progress check task
        from app.workers.progress_check import update_progress_task
        task_result = update_progress_task.delay(claim_id)
        
        # Log the manual progress update
        progress_update_log = ActivityLog(
            claim_id=claim_id,
            activity_type=ActivityType.MANUAL_UPDATE,
            description="Manual progress update triggered via API",
            timestamp=datetime.utcnow(),
            activity_metadata={"task_id": task_result.id}
        )
        
        db.add(progress_update_log)
        await db.commit()
        
        logger.info(f"Manual progress update triggered for claim {claim_id}")
        
        return {
            "message": f"Progress update triggered for claim {claim_id}",
            "claim_id": claim_id,
            "task_id": task_result.id,
            "status": "scheduled"
        }
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to trigger progress update for claim {claim_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error triggering progress update: {str(e)}"
        )

@router.get("/progress/{claim_id}/commits")
async def get_claim_commits(
    claim_id: int,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get commit activity for a specific claim
    """
    
    # Verify claim exists
    stmt = select(Claim).where(Claim.id == claim_id)
    result = await db.execute(stmt)
    claim = result.scalar_one_or_none()
    
    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Claim {claim_id} not found"
        )
    
    # Get progress tracking
    progress_stmt = select(ProgressTracking).where(
        ProgressTracking.claim_id == claim_id
    )
    progress_result = await db.execute(progress_stmt)
    progress_tracking = progress_result.scalar_one_or_none()
    
    if not progress_tracking:
        return {
            "claim_id": claim_id,
            "commit_count": 0,
            "last_commit_date": None,
            "commits": []
        }
    
    # Fetch real commit data from GitHub API
    commits = []
    try:
        from app.services.github_service import get_github_service
        from datetime import datetime, timezone
        
        github_service = get_github_service()
        
        if claim.issue and claim.issue.repository:
            # Get commits by user since claim was made
            since_date = claim.claim_timestamp.replace(tzinfo=timezone.utc)
            commits_data = await github_service.get_user_commits(
                owner=claim.issue.repository.owner,
                name=claim.issue.repository.name,
                username=claim.github_username,
                since=since_date
            )
            commits = commits_data
    except Exception as e:
        logger.warning(f"Could not fetch commits for claim {claim_id}: {e}")
    
    return {
        "claim_id": claim_id,
        "commit_count": len(commits),
        "last_commit_date": commits[0]['author']['date'] if commits else (progress_tracking.last_commit_date.isoformat() if progress_tracking.last_commit_date else None),
        "commits": commits
    }

@router.get("/progress/{claim_id}/prs") 
async def get_claim_pull_requests(
    claim_id: int,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get pull request activity for a specific claim
    """
    
    # Verify claim exists
    stmt = select(Claim).where(Claim.id == claim_id)
    result = await db.execute(stmt)
    claim = result.scalar_one_or_none()
    
    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Claim {claim_id} not found"
        )
    
    # Get progress tracking
    progress_stmt = select(ProgressTracking).where(
        ProgressTracking.claim_id == claim_id
    )
    progress_result = await db.execute(progress_stmt)
    progress_tracking = progress_result.scalar_one_or_none()
    
    # Fetch real pull request data from GitHub API
    pull_requests = []
    try:
        from app.services.github_service import get_github_service
        
        github_service = get_github_service()
        
        if claim.issue and claim.issue.repository:
            # Get PRs that reference this issue
            prs_data = await github_service.get_pull_requests_for_issue(
                owner=claim.issue.repository.owner,
                name=claim.issue.repository.name,
                issue_number=claim.issue.github_issue_number
            )
            
            # Filter PRs by the claim user
            for pr in prs_data:
                if pr['user']['login'] == claim.github_username:
                    pull_requests.append(pr)
                    
    except Exception as e:
        logger.warning(f"Could not fetch PRs for claim {claim_id}: {e}")
        
        # Fallback to progress tracking data if available
        if progress_tracking and progress_tracking.pr_number:
            pull_requests = [{
                "number": progress_tracking.pr_number,
                "status": progress_tracking.pr_status,
                "detected_from": progress_tracking.detected_from,
                "updated_at": progress_tracking.updated_at.isoformat()
            }]
    
    return {
        "claim_id": claim_id,
        "pr_number": pull_requests[0]['number'] if pull_requests else (progress_tracking.pr_number if progress_tracking else None),
        "pr_status": pull_requests[0]['state'] if pull_requests else (progress_tracking.pr_status if progress_tracking else None),
        "pull_requests": pull_requests
    }
