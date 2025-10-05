"""
Dashboard Endpoints
As specified in MD file API Design section:
- GET /api/dashboard/stats
- GET /api/dashboard/repositories 
- GET /api/dashboard/users
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, case
from typing import List, Dict
from datetime import datetime, timedelta

from app.db.database import get_async_session
from app.db.models import Repository, Claim, Issue, ActivityLog
from app.db.models.claims import ClaimStatus

router = APIRouter()

@router.get("/dashboard/stats")
async def get_dashboard_stats(db: AsyncSession = Depends(get_async_session)):
    """
    Overall system statistics
    As specified in MD file: GET /api/dashboard/stats
    """
    
    # Total claims
    total_claims_stmt = select(func.count(Claim.id))
    total_claims_result = await db.execute(total_claims_stmt)
    total_claims = total_claims_result.scalar()
    
    # Active claims  
    active_claims_stmt = select(func.count(Claim.id)).where(Claim.status == ClaimStatus.ACTIVE)
    active_claims_result = await db.execute(active_claims_stmt)
    active_claims = active_claims_result.scalar()
    
    # Released claims
    released_claims_stmt = select(func.count(Claim.id)).where(Claim.status == ClaimStatus.RELEASED)
    released_claims_result = await db.execute(released_claims_stmt)
    released_claims = released_claims_result.scalar()
    
    # Completed claims
    completed_claims_stmt = select(func.count(Claim.id)).where(Claim.status == ClaimStatus.COMPLETED)
    completed_claims_result = await db.execute(completed_claims_stmt)
    completed_claims = completed_claims_result.scalar()
    
    # Claims by confidence score distribution  
    confidence_bucket = func.floor(Claim.confidence_score / 10) * 10
    confidence_stmt = select(
        confidence_bucket.label("confidence_range"),
        func.count(Claim.id).label("count")
    ).group_by(confidence_bucket)
    confidence_result = await db.execute(confidence_stmt)
    confidence_data = confidence_result.all()
    confidence_distribution = {str(int(row.confidence_range)): row.count for row in confidence_data}
    
    # Recent activity (last 7 days)
    week_ago = datetime.utcnow() - timedelta(days=7)
    recent_claims_stmt = select(func.count(Claim.id)).where(
        Claim.claim_timestamp >= week_ago
    )
    recent_claims_result = await db.execute(recent_claims_stmt)
    recent_claims = recent_claims_result.scalar()
    
    # Auto-release rate
    auto_released_stmt = select(func.count(Claim.id)).where(
        Claim.release_reason == "auto_released_after_max_nudges"
    )
    auto_released_result = await db.execute(auto_released_stmt)
    auto_released = auto_released_result.scalar()
    
    # Average time to release
    released_with_time_stmt = select(Claim).where(
        Claim.status == ClaimStatus.RELEASED,
        Claim.auto_release_timestamp.isnot(None)
    )
    released_with_time_result = await db.execute(released_with_time_stmt)
    released_with_time = released_with_time_result.scalars().all()
    
    avg_time_to_release = None
    if released_with_time:
        total_time = sum([
            (claim.auto_release_timestamp - claim.claim_timestamp).total_seconds()
            for claim in released_with_time
        ])
        avg_time_to_release = total_time / len(released_with_time) / 86400  # days
    
    return {
        "overview": {
            "total_claims": total_claims,
            "active_claims": active_claims,
            "released_claims": released_claims,
            "completed_claims": completed_claims
        },
        "metrics": {
            "recent_claims_7d": recent_claims,
            "auto_release_rate": auto_released / max(total_claims, 1) * 100,
            "avg_time_to_release_days": round(avg_time_to_release or 0, 1)
        },
        "confidence_distribution": confidence_distribution,
        "generated_at": datetime.utcnow().isoformat()
    }

@router.get("/dashboard/repositories")
async def get_repository_metrics(db: AsyncSession = Depends(get_async_session)):
    """
    Repository-specific metrics
    As specified in MD file: GET /api/dashboard/repositories
    """
    
    # Active claims per repository
    repo_claims_stmt = select(
        Repository.owner_name,
        Repository.name,
        Repository.id,
        func.count(Claim.id).label("active_claims")
    ).select_from(
        Repository.__table__.join(Issue.__table__, Repository.id == Issue.repository_id)
        .join(Claim.__table__, Issue.id == Claim.issue_id)
    ).where(
        Claim.status == ClaimStatus.ACTIVE
    ).group_by(
        Repository.id, Repository.owner_name, Repository.name
    ).order_by(desc("active_claims"))
    
    repo_claims_result = await db.execute(repo_claims_stmt)
    repo_claims = repo_claims_result.all()
    
    # Success rate per repository (claims completed vs total)
    repo_success_rates = []
    
    # Get all monitored repositories
    monitored_repos_stmt = select(Repository).where(Repository.is_monitored == True)
    monitored_repos_result = await db.execute(monitored_repos_stmt)
    monitored_repos = monitored_repos_result.scalars().all()
    
    for repo in monitored_repos:
        # Total claims for this repository
        total_claims_stmt = select(func.count(Claim.id)).select_from(
            Claim.__table__.join(Issue.__table__, Claim.issue_id == Issue.id)
        ).where(Issue.repository_id == repo.id)
        total_claims_result = await db.execute(total_claims_stmt)
        total_claims = total_claims_result.scalar()
        
        # Completed claims for this repository
        completed_claims_stmt = select(func.count(Claim.id)).select_from(
            Claim.__table__.join(Issue.__table__, Claim.issue_id == Issue.id)
        ).where(
            Issue.repository_id == repo.id,
            Claim.status == ClaimStatus.COMPLETED
        )
        completed_claims_result = await db.execute(completed_claims_stmt)
        completed_claims = completed_claims_result.scalar()
        
        success_rate = completed_claims / max(total_claims, 1) * 100
        
        repo_success_rates.append({
            "repository": f"{repo.owner_name}/{repo.name}",
            "repository_id": repo.id,
            "total_claims": total_claims,
            "completed_claims": completed_claims,
            "success_rate": round(success_rate, 1)
        })
    
    return {
        "active_claims_by_repo": [
            {
                "repository": f"{r.owner_name}/{r.name}",
                "repository_id": r.id,
                "active_claims": r.active_claims
            }
            for r in repo_claims
        ],
        "success_rates": repo_success_rates,
        "generated_at": datetime.utcnow().isoformat()
    }

@router.get("/dashboard/users")
async def get_user_metrics(db: AsyncSession = Depends(get_async_session)):
    """
    User activity metrics
    As specified in MD file: GET /api/dashboard/users
    """
    
    # Claim completion rates by user
    user_stats_stmt = select(
        Claim.github_username,
        func.count(Claim.id).label("total_claims"),
        func.sum(case((Claim.status == ClaimStatus.COMPLETED, 1), else_=0)).label("completed_claims"),
        func.sum(case((Claim.status == ClaimStatus.RELEASED, 1), else_=0)).label("released_claims")
    ).group_by(Claim.github_username)\
     .having(func.count(Claim.id) > 0)\
     .order_by(desc("total_claims"))\
     .limit(50)
     
    user_stats_result = await db.execute(user_stats_stmt)
    user_stats = user_stats_result.all()
    
    # Top contributors (by completion rate)
    top_contributors = []
    frequent_claimers = []
    
    for user in user_stats:
        completion_rate = user.completed_claims / user.total_claims * 100
        
        user_data = {
            "username": user.github_username,
            "total_claims": user.total_claims,
            "completed_claims": user.completed_claims,
            "released_claims": user.released_claims,
            "completion_rate": round(completion_rate, 1)
        }
        
        # Top contributors (high completion rate with reasonable claim count)
        if completion_rate >= 80 and user.total_claims >= 3:
            top_contributors.append(user_data)
        
        # Frequent claimers (high claim count, any completion rate)
        if user.total_claims >= 10:
            frequent_claimers.append(user_data)
    
    # Sort lists
    top_contributors.sort(key=lambda x: x["completion_rate"], reverse=True)
    frequent_claimers.sort(key=lambda x: x["total_claims"], reverse=True)
    
    return {
        "top_contributors": top_contributors[:20],
        "frequent_claimers": frequent_claimers[:20],
        "user_distribution": {
            "total_users": len(user_stats),
            "high_performers": len([u for u in user_stats if (u.completed_claims / u.total_claims) >= 0.8]),
            "frequent_users": len([u for u in user_stats if u.total_claims >= 5]),
        },
        "generated_at": datetime.utcnow().isoformat()
    }

@router.get("/dashboard/activity")
async def get_recent_activity(db: AsyncSession = Depends(get_async_session)):
    """
    Recent system activity feed
    """
    
    # Get recent activity logs with claim data
    recent_activities_stmt = select(ActivityLog, Claim).join(
        Claim, ActivityLog.claim_id == Claim.id
    ).order_by(desc(ActivityLog.timestamp)).limit(100)
    
    recent_activities_result = await db.execute(recent_activities_stmt)
    recent_activities_data = recent_activities_result.all()
    
    activity_feed = []
    for activity, claim in recent_activities_data:
        activity_feed.append({
            "id": activity.id,
            "type": activity.activity_type,
            "description": activity.description,
            "timestamp": activity.timestamp.isoformat(),
            "claim_id": activity.claim_id,
            "username": claim.github_username if claim else None,
            "metadata": activity.activity_metadata
        })
    
    return {
        "recent_activities": activity_feed,
        "generated_at": datetime.utcnow().isoformat()
    }