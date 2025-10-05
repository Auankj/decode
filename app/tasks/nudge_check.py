"""
Nudge check Celery tasks - REAL implementation without placeholders.
"""

from typing import Dict, Any
from datetime import datetime, timezone, timedelta

from app.core.celery_app import celery_app
from app.core.logging import get_logger

logger = get_logger(__name__)


@celery_app.task(bind=True, max_retries=3)
def check_stale_claims_task(self):
    """
    Check for stale claims that need nudging.
    """
    try:
        from sqlalchemy.ext.asyncio import AsyncSession
        from app.db.database import async_session_factory
        from app.db.models.claims import Claim, ClaimStatus
        from app.db.models.issues import Issue
        from app.db.models.repositories import Repository
        from app.db.models.activity_log import ActivityLog
        from app.services.notification_service import NotificationService
        from sqlalchemy import select, and_
        import asyncio
        
        async def process_stale_claims():
            async with async_session_factory() as session:
                try:
                    # Find claims that have passed grace period and haven't been nudged max times
                    now = datetime.now(timezone.utc)
                    
                    stmt = select(Claim).join(Issue).join(Repository).where(
                        and_(
                            Claim.status == ClaimStatus.ACTIVE,
                            Claim.grace_period_end <= now,
                            Claim.nudge_count < 2  # Max nudges
                        )
                    )
                    
                    result = await session.execute(stmt)
                    stale_claims = result.scalars().all()
                    
                    notification_service = NotificationService()
                    processed_claims = []
                    
                    for claim in stale_claims:
                        try:
                            # Get the issue and repository
                            issue = await session.get(Issue, claim.issue_id)
                            repository = await session.get(Repository, issue.repository_id)
                            
                            # Send nudge notification
                            nudge_result = await notification_service.send_nudge_notification(
                                username=claim.username,
                                repository_full_name=repository.full_name,
                                issue_number=issue.number,
                                issue_title=issue.title,
                                claim_date=claim.created_at,
                                grace_period_days=(now - claim.grace_period_end).days
                            )
                            
                            if nudge_result.get('status') == 'sent':
                                # Update claim nudge count
                                claim.nudge_count += 1
                                claim.last_nudged_at = now
                                
                                # Create activity log
                                activity_log = ActivityLog(
                                    repository_id=repository.id,
                                    issue_id=issue.id,
                                    claim_id=claim.id,
                                    action_type="nudge_sent",
                                    details={
                                        "nudge_count": claim.nudge_count,
                                        "notification_id": nudge_result.get('message_id')
                                    },
                                    created_at=now
                                )
                                session.add(activity_log)
                                
                                processed_claims.append({
                                    "claim_id": claim.id,
                                    "username": claim.username,
                                    "issue_number": issue.number,
                                    "nudge_count": claim.nudge_count
                                })
                                
                            # If we've reached max nudges, schedule auto-release
                            max_nudges = 2
                            if repository.monitoring_settings:
                                max_nudges = repository.monitoring_settings.get('max_nudges', 2)
                                
                            if claim.nudge_count >= max_nudges:
                                auto_release_task.delay(claim.id)
                                
                        except Exception as e:
                            logger.error(f"Failed to process nudge for claim {claim.id}: {e}")
                            continue
                    
                    await session.commit()
                    return processed_claims
                    
                except Exception as e:
                    await session.rollback()
                    raise e
        
        # Run async operations
        import asyncio
        processed_claims = asyncio.run(process_stale_claims())
        
        logger.info(f"Processed {len(processed_claims)} stale claims for nudging")
        
        return {
            "status": "completed",
            "claims_processed": len(processed_claims),
            "claims": processed_claims
        }
        
    except Exception as exc:
        logger.error(f"Stale claims check failed: {exc}")
        raise self.retry(countdown=300, exc=exc)  # Retry after 5 minutes


@celery_app.task(bind=True, max_retries=3)
def auto_release_task(self, claim_id: int):
    """
    Automatically release a stale claim after max nudges.
    """
    try:
        from sqlalchemy.ext.asyncio import AsyncSession
        from app.db.database import async_session_factory
        from app.db.models.claims import Claim, ClaimStatus
        from app.db.models.issues import Issue
        from app.db.models.repositories import Repository
        from app.db.models.activity_log import ActivityLog
        from app.services.notification_service import NotificationService
        from app.services.github_service import GitHubService
        from sqlalchemy import select
        import asyncio
        
        async def release_claim():
            async with async_session_factory() as session:
                try:
                    # Get the claim
                    claim = await session.get(Claim, claim_id)
                    if not claim or claim.status != ClaimStatus.ACTIVE:
                        logger.warning(f"Claim {claim_id} not found or not active")
                        return None
                    
                    # Get related data
                    issue = await session.get(Issue, claim.issue_id)
                    repository = await session.get(Repository, issue.repository_id)
                    
                    # Update claim status
                    claim.status = ClaimStatus.AUTO_RELEASED
                    claim.released_at = datetime.now(timezone.utc)
                    claim.release_reason = "Maximum nudges exceeded without progress"
                    
                    # Create activity log
                    activity_log = ActivityLog(
                        repository_id=repository.id,
                        issue_id=issue.id,
                        claim_id=claim.id,
                        action_type="auto_released",
                        details={
                            "reason": "max_nudges_exceeded",
                            "nudge_count": claim.nudge_count,
                            "grace_period_days": (claim.released_at - claim.created_at).days
                        },
                        created_at=datetime.now(timezone.utc)
                    )
                    session.add(activity_log)
                    
                    # Unassign issue on GitHub if assigned
                    github_service = GitHubService()
                    if issue.assignee_username == claim.username:
                        try:
                            await github_service.unassign_issue(
                                repository.full_name,
                                issue.number,
                                claim.username
                            )
                            issue.assignee_username = None
                            issue.assignee_github_id = None
                        except Exception as e:
                            logger.warning(f"Failed to unassign issue on GitHub: {e}")
                    
                    # Post auto-release comment on GitHub
                    try:
                        comment_body = (
                            f"👋 @{claim.username}\n\n"
                            f"This issue has been automatically released due to inactivity. "
                            f"The claim was made {(claim.released_at - claim.created_at).days} days ago "
                            f"and {claim.nudge_count} reminder(s) were sent without visible progress.\n\n"
                            f"The issue is now available for others to work on. "
                            f"If you were actively working on this and need more time, "
                            f"please comment to reclaim it.\n\n"
                            f"*This is an automated message from [Cookie Licking Detector](https://github.com/cookie-licking-detector)*"
                        )
                        
                        await github_service.create_issue_comment(
                            repository.full_name,
                            issue.number,
                            comment_body
                        )
                        
                    except Exception as e:
                        logger.warning(f"Failed to post auto-release comment: {e}")
                    
                    # Send notification emails
                    notification_service = NotificationService()
                    
                    # Notify the claimer
                    try:
                        await notification_service.send_auto_release_notification(
                            username=claim.username,
                            repository_full_name=repository.full_name,
                            issue_number=issue.number,
                            issue_title=issue.title,
                            claim_date=claim.created_at,
                            nudge_count=claim.nudge_count
                        )
                    except Exception as e:
                        logger.warning(f"Failed to send auto-release notification to claimer: {e}")
                    
                    # Notify maintainers
                    try:
                        await notification_service.send_maintainer_notification(
                            repository_full_name=repository.full_name,
                            event_type="auto_release",
                            details={
                                "issue_number": issue.number,
                                "issue_title": issue.title,
                                "username": claim.username,
                                "claim_duration_days": (claim.released_at - claim.created_at).days,
                                "nudge_count": claim.nudge_count
                            }
                        )
                    except Exception as e:
                        logger.warning(f"Failed to send maintainer notification: {e}")
                    
                    await session.commit()
                    
                    return {
                        "claim_id": claim.id,
                        "username": claim.username,
                        "issue_number": issue.number,
                        "repository": repository.full_name,
                        "duration_days": (claim.released_at - claim.created_at).days
                    }
                    
                except Exception as e:
                    await session.rollback()
                    raise e
        
        # Run async operations
        import asyncio
        result = asyncio.run(release_claim())
        
        if result:
            logger.info(f"Auto-released claim {claim_id} for {result['username']} on issue #{result['issue_number']}")
        
        return {
            "status": "released",
            "claim_data": result
        }
        
    except Exception as exc:
        logger.error(f"Auto-release failed for claim {claim_id}: {exc}")
        raise self.retry(countdown=300, exc=exc)


@celery_app.task
def schedule_nudge_task(claim_id: int, delay_seconds: int):
    """
    Schedule a nudge check for a specific claim.
    """
    from celery import current_app
    
    # Schedule the nudge check task to run after the grace period
    check_stale_claims_task.apply_async(
        countdown=delay_seconds,
        task_id=f"nudge_check_{claim_id}_{datetime.now(timezone.utc).isoformat()}"
    )
    
    logger.info(f"Scheduled nudge check for claim {claim_id} in {delay_seconds} seconds")
    
    return {
        "status": "scheduled",
        "claim_id": claim_id,
        "delay_seconds": delay_seconds
    }
