"""
Claim Management Endpoints
As specified in MD file API Design section:
- GET /api/claims
- GET /api/claims/{id}
- POST /api/claims/{id}/nudge
- POST /api/claims/{id}/release
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.db.database import get_async_session
from app.db.models import Claim, ActivityLog, Issue, Repository, ClaimStatus
from app.workers.nudge_check import process_nudge_check
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()

# Pydantic models
class ClaimResponse(BaseModel):
    id: int
    issue_id: int
    github_user_id: int
    github_username: str
    claim_text: Optional[str]
    claim_timestamp: datetime
    status: str
    confidence_score: Optional[int]
    first_nudge_sent_at: Optional[datetime]
    last_activity_timestamp: datetime
    auto_release_timestamp: Optional[datetime]
    release_reason: Optional[str]
    
    # Related issue info
    issue_number: Optional[int]
    issue_title: Optional[str]
    repository_name: Optional[str]
    
    class Config:
        from_attributes = True

class ClaimListResponse(BaseModel):
    claims: List[ClaimResponse]
    total_count: int
    page: int
    per_page: int

@router.get("/claims", response_model=ClaimListResponse)
async def list_claims(
    status: Optional[str] = Query(None, description="Filter by claim status"),
    repo: Optional[str] = Query(None, description="Filter by repository (owner/name)"),
    user: Optional[str] = Query(None, description="Filter by GitHub username"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(50, ge=1, le=200, description="Items per page"),
    db: AsyncSession = Depends(get_async_session)
):
    """
    List all claims with filtering
    As specified in MD file: GET /api/claims
    """
    
    # Build base query with joins
    stmt = select(Claim, Issue, Repository).join(
        Issue, Claim.issue_id == Issue.id
    ).join(
        Repository, Issue.repository_id == Repository.id
    )
    
    # Apply filters
    if status:
        # Convert string status to enum if needed
        status_enum = ClaimStatus(status) if hasattr(ClaimStatus, status.upper()) else status
        stmt = stmt.where(Claim.status == status_enum)
    
    if repo:
        if "/" in repo:
            owner, name = repo.split("/", 1)
            stmt = stmt.where(Repository.owner_name == owner, Repository.name == name)
    
    if user:
        stmt = stmt.where(Claim.github_username.ilike(f"%{user}%"))
    
    # Get total count - use the same join pattern as the main query
    count_stmt = select(func.count(Claim.id)).select_from(
        Claim.__table__.join(Issue.__table__, Claim.issue_id == Issue.id).join(
            Repository.__table__, Issue.repository_id == Repository.id
        )
    )
    if status:
        status_enum = ClaimStatus(status) if hasattr(ClaimStatus, status.upper()) else status
        count_stmt = count_stmt.where(Claim.status == status_enum)
    if repo and "/" in repo:
        owner, name = repo.split("/", 1)
        count_stmt = count_stmt.where(Repository.owner_name == owner, Repository.name == name)
    if user:
        count_stmt = count_stmt.where(Claim.github_username.ilike(f"%{user}%"))
    
    count_result = await db.execute(count_stmt)
    total_count = count_result.scalar()
    
    # Apply pagination
    offset = (page - 1) * per_page
    stmt = stmt.offset(offset).limit(per_page)
    result = await db.execute(stmt)
    claims_data = result.all()
    
    # Format response
    claim_responses = []
    for claim, issue, repository in claims_data:
        claim_data = ClaimResponse(
            id=claim.id,
            issue_id=claim.issue_id,
            github_user_id=claim.github_user_id,
            github_username=claim.github_username,
            claim_text=claim.claim_text,
            claim_timestamp=claim.claim_timestamp,
            status=claim.status.value if hasattr(claim.status, 'value') else claim.status,
            confidence_score=claim.confidence_score,
            first_nudge_sent_at=claim.first_nudge_sent_at,
            last_activity_timestamp=claim.last_activity_timestamp,
            auto_release_timestamp=claim.auto_release_timestamp,
            release_reason=claim.release_reason,
            issue_number=issue.github_issue_number if issue else None,
            issue_title=issue.title if issue else None,
            repository_name=f"{repository.owner_name}/{repository.name}" if repository else None
        )
        claim_responses.append(claim_data)
    
    return ClaimListResponse(
        claims=claim_responses,
        total_count=total_count,
        page=page,
        per_page=per_page
    )

@router.get("/claims/{claim_id}")
async def get_claim_details(
    claim_id: int,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get specific claim details
    As specified in MD file: GET /api/claims/{id}
    """
    
    # Get claim with related data
    stmt = select(Claim, Issue, Repository).join(
        Issue, Claim.issue_id == Issue.id
    ).join(
        Repository, Issue.repository_id == Repository.id
    ).where(Claim.id == claim_id)
    
    result = await db.execute(stmt)
    claim_data = result.first()
    
    if not claim_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Claim {claim_id} not found"
        )
    
    claim, issue, repository = claim_data
    
    # Get activity history
    activities_stmt = select(ActivityLog).where(
        ActivityLog.claim_id == claim_id
    ).order_by(ActivityLog.timestamp.desc())
    
    activities_result = await db.execute(activities_stmt)
    activities = activities_result.scalars().all()
    
    activity_history = [
        {
            "id": activity.id,
            "type": activity.activity_type,
            "description": activity.description,
            "timestamp": activity.timestamp.isoformat(),
            "metadata": activity.activity_metadata
        }
        for activity in activities
    ]
    
    return {
        "claim": {
            "id": claim.id,
            "issue_id": claim.issue_id,
            "github_user_id": claim.github_user_id,
            "github_username": claim.github_username,
            "claim_text": claim.claim_text,
            "claim_timestamp": claim.claim_timestamp.isoformat(),
            "status": claim.status,
            "confidence_score": claim.confidence_score,
            "context_metadata": claim.context_metadata,
            "first_nudge_sent_at": claim.first_nudge_sent_at.isoformat() if claim.first_nudge_sent_at else None,
            "last_activity_timestamp": claim.last_activity_timestamp.isoformat(),
            "auto_release_timestamp": claim.auto_release_timestamp.isoformat() if claim.auto_release_timestamp else None,
            "release_reason": claim.release_reason
        },
        "issue": {
            "id": issue.id,
            "github_issue_number": issue.github_issue_number,
            "title": issue.title,
            "description": issue.description,
            "status": issue.status.value if hasattr(issue.status, 'value') else issue.status,
            "repository": f"{repository.owner_name}/{repository.name}" if repository else None
        } if issue else None,
        "activity_history": activity_history
    }

@router.post("/claims/{claim_id}/nudge")
async def manually_send_nudge(
    claim_id: int,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Manually send a nudge for a claim
    As specified in MD file: POST /api/claims/{id}/nudge
    """
    
    # Verify claim exists and is active
    stmt = select(Claim).where(Claim.id == claim_id)
    result = await db.execute(stmt)
    claim = result.scalar_one_or_none()
    
    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Claim {claim_id} not found"
        )
    
    if claim.status != ClaimStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot nudge claim with status: {claim.status.value}"
        )
    
    try:
        # Schedule nudge check (which will send the nudge)
        result = process_nudge_check.delay(claim_id)
        
        # Log the manual nudge action
        from app.db.models import ActivityType
        manual_nudge_log = ActivityLog(
            claim_id=claim_id,
            activity_type=ActivityType.PROGRESS_NUDGE,
            description="Manual nudge triggered via API",
            activity_metadata={"task_id": result.id, "manual_trigger": True}
        )
        
        db.add(manual_nudge_log)
        await db.commit()
        
        return {
            "message": f"Nudge scheduled for claim {claim_id}",
            "claim_id": claim_id,
            "task_id": result.id,
            "status": "scheduled"
        }
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error scheduling nudge: {str(e)}"
        )

@router.post("/claims/{claim_id}/release")
async def manually_release_claim(
    claim_id: int,
    reason: Optional[str] = None,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Manually release a claim
    As specified in MD file: POST /api/claims/{id}/release
    """
    
    # Verify claim exists and can be released
    stmt = select(Claim).where(Claim.id == claim_id)
    result = await db.execute(stmt)
    claim = result.scalar_one_or_none()
    
    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Claim {claim_id} not found"
        )
    
    if claim.status not in [ClaimStatus.ACTIVE, "active", "inactive"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot release claim with status: {claim.status}"
        )
    
    try:
        # Update claim status
        claim.status = ClaimStatus.RELEASED
        claim.auto_release_timestamp = datetime.utcnow()
        claim.release_reason = reason or "manual_release_via_api"
        
        # Log the manual release
        from app.db.models import ActivityType
        release_log = ActivityLog(
            claim_id=claim_id,
            activity_type=ActivityType.MANUAL_RELEASE,
            description="Claim manually released via API",
            timestamp=datetime.utcnow(),
            activity_metadata={"reason": reason}
        )
        
        db.add(release_log)
        await db.commit()
        
        # Remove GitHub assignment if exists
        try:
            from app.services.github_service import GitHubService
            github_service = GitHubService()
            
            if claim.issue and claim.issue.repository:
                repo_full_name = f"{claim.issue.repository.owner}/{claim.issue.repository.name}"
                await github_service.unassign_issue(
                    repo_full_name,
                    claim.issue.github_issue_number,
                    claim.github_username
                )
                logger.info(f"Removed GitHub assignment for {claim.github_username} on {repo_full_name}#{claim.issue.github_issue_number}")
        except Exception as e:
            logger.warning(f"Failed to remove GitHub assignment: {e}")
        
        # Notify maintainers
        try:
            from app.services.notification_service import NotificationService
            notification_service = NotificationService()
            
            if claim.issue and claim.issue.repository:
                await notification_service.send_maintainer_notification(
                    repository_full_name=f"{claim.issue.repository.owner}/{claim.issue.repository.name}",
                    event_type="manual_release",
                    details={
                        "issue_number": claim.issue.github_issue_number,
                        "issue_title": claim.issue.title,
                        "username": claim.github_username,
                        "release_reason": claim.release_reason,
                        "manual_release": True
                    }
                )
                logger.info(f"Sent maintainer notification for manual release of claim {claim_id}")
        except Exception as e:
            logger.warning(f"Failed to send maintainer notification: {e}")
        
        return {
            "message": f"Claim {claim_id} released successfully",
            "claim_id": claim_id,
            "status": "released",
            "release_timestamp": claim.auto_release_timestamp.isoformat(),
            "reason": claim.release_reason
        }
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error releasing claim: {str(e)}"
        )

@router.get("/claims/{claim_id}/activity")
async def get_claim_activity(
    claim_id: int,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get activity history for a specific claim
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
    
    # Get activity history
    activities_stmt = select(ActivityLog).where(
        ActivityLog.claim_id == claim_id
    ).order_by(ActivityLog.timestamp.desc())
    
    activities_result = await db.execute(activities_stmt)
    activities = activities_result.scalars().all()
    
    return {
        "claim_id": claim_id,
        "activities": [
            {
                "id": activity.id,
                "type": activity.activity_type,
                "description": activity.description,
                "timestamp": activity.timestamp.isoformat(),
                "metadata": activity.activity_metadata
            }
            for activity in activities
        ]
    }