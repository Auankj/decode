"""
Comment analysis Celery task.
"""

from typing import Dict, Any
from app.core.celery_app import celery_app
from app.core.logging import get_logger

logger = get_logger(__name__)


@celery_app.task(bind=True, max_retries=3)
def analyze_comment_task(self, comment_data: Dict[str, Any]):
    """
    Analyze a comment for claims (Celery task).
    """
    try:
        from sqlalchemy.ext.asyncio import AsyncSession
        from app.db.database import get_async_session_factory
        from app.services.pattern_matcher import ClaimPatternMatcher
        from app.db.models.claims import Claim
        from app.db.models.activity_log import ActivityLog
        from app.db.models.issues import Issue
        from app.db.models.repositories import Repository
        from datetime import datetime, timezone, timedelta
        from sqlalchemy import select
        
        logger.info(f"Analyzing comment {comment_data.get('comment_id')} from issue #{comment_data.get('issue_number')}")
        
        # Analyze the comment using pattern matcher
        matcher = ClaimPatternMatcher()
        comment_body = comment_data.get('comment_body', '')
        comment_user = comment_data.get('comment_user', {})
        issue_data = comment_data.get('issue_data', {})
        
        analysis_result = matcher.analyze_comment(
            comment_text=comment_body,
            comment_data=comment_user,
            issue_data=issue_data
        )
        
        # If no claim detected, return early
        if not analysis_result.get('is_claim', False):
            logger.info(f"No claim detected in comment {comment_data.get('comment_id')}")
            return {
                "status": "no_claim",
                "comment_id": comment_data.get("comment_id"),
                "confidence_score": analysis_result.get('confidence_score', 0)
            }
        
        # Use sync database operations to avoid event loop issues
        from sqlalchemy import create_engine, text
        from sqlalchemy.orm import sessionmaker
        from app.core.config import get_settings
        
        settings = get_settings()
        sync_db_url = settings.DATABASE_URL
        if "postgresql+asyncpg://" in sync_db_url:
            sync_db_url = sync_db_url.replace("postgresql+asyncpg://", "postgresql://")
        elif sync_db_url.startswith("postgresql://"):
            pass  # Already sync URL
            
        # Create engine with timeouts to prevent hanging
        sync_engine = create_engine(
            sync_db_url, 
            pool_timeout=10, 
            pool_pre_ping=True,
            connect_args={"connect_timeout": 10}
        )
        SessionLocal = sessionmaker(bind=sync_engine)
        
        claim_id = None
        session = SessionLocal()
        try:
            # Get the issue from database
            issue = session.query(Issue).filter(
                Issue.github_issue_number == comment_data.get('issue_number')
            ).first()
            
            if not issue:
                logger.warning(f"Issue {comment_data.get('issue_id')} not found in database")
                return {'status': 'no_issue_found'}
            
            # Check if this user already has an active claim on this issue
            from app.db.models.claims import ClaimStatus
            existing_claim = session.query(Claim).filter(
                Claim.issue_id == issue.id,
                Claim.github_username == comment_data.get('comment_user', {}).get('login'),
                Claim.status == ClaimStatus.ACTIVE
            ).first()
            
            if existing_claim:
                logger.info(f"User {comment_data.get('comment_user', {}).get('login')} already has active claim on issue {issue.github_issue_number}")
                claim_id = existing_claim.id
            else:
                # Get repository
                repository = session.query(Repository).filter(
                    Repository.id == issue.repository_id
                ).first()
                
                if not repository:
                    # Fallback: try to find by github_repo_id
                    repository = session.query(Repository).filter(
                        Repository.github_repo_id == issue.github_repo_id
                    ).first()
                
                repository_id = repository.id if repository else None
                if not repository_id:
                    logger.warning(f"No repository found for issue {issue.id}, cannot create claim")
                    return {'status': 'no_repository_found'}
                    
                new_claim = Claim(
                    issue_id=issue.id,
                    repository_id=repository_id,
                    github_username=comment_data.get('comment_user', {}).get('login'),
                    github_user_id=comment_data.get('comment_user', {}).get('id'),
                    claim_text=comment_body,
                    claim_comment_id=comment_data.get('comment_id'),
                    confidence_score=analysis_result.get('final_score', 0),
                    context_metadata=analysis_result.get('analysis_metadata', {}),
                    status=ClaimStatus.ACTIVE,
                    claim_timestamp=datetime.now(timezone.utc),
                    last_activity_timestamp=datetime.now(timezone.utc)
                )
                
                session.add(new_claim)
                session.commit()
                session.refresh(new_claim)
                claim_id = new_claim.id
                
                # Create activity log entry
                from app.db.models.activity_log import ActivityType
                activity_log = ActivityLog(
                    claim_id=new_claim.id,
                    activity_type=ActivityType.CLAIM_DETECTED,
                    description=f"Claim detected by {comment_data.get('comment_user', {}).get('login')}",
                    activity_metadata={
                        "comment_id": comment_data.get('comment_id'),
                        "username": comment_data.get('comment_user', {}).get('login'),
                        "confidence_score": analysis_result.get('final_score'),
                        "detected_patterns": [],  # Skip patterns in metadata to avoid JSON issues
                        "context_boost": analysis_result.get('context_boost', 0)
                    },
                    timestamp=datetime.now(timezone.utc)
                )
                
                session.add(activity_log)
                session.commit()
                
        except Exception as e:
            session.rollback()
            logger.error(f"Database error: {e}")
            raise e
        finally:
            session.close()
        
        if claim_id:
            # Queue nudge task for later with default grace period
            from app.tasks.nudge_check import schedule_nudge_task
            default_grace_period_seconds = 7 * 24 * 60 * 60  # 7 days in seconds
            schedule_nudge_task.delay(claim_id, default_grace_period_seconds)
            
            logger.info(f"Successfully created claim {claim_id} for comment {comment_data.get('comment_id')}")
        
        return {
            "status": "claim_created" if claim_id else "claim_exists",
            "comment_id": comment_data.get("comment_id"),
            "confidence_score": analysis_result.get('final_score', 0),
            "claim_id": claim_id,
            "patterns_detected": len(analysis_result.get('detected_patterns', []))
        }
        
    except Exception as exc:
        logger.error(f"Comment analysis failed: {exc}")
        raise self.retry(countdown=60, exc=exc)


@celery_app.task
def batch_analyze_comments(comment_list: list):
    """
    Batch analyze multiple comments.
    """
    results = []
    for comment_data in comment_list:
        result = analyze_comment_task.delay(comment_data)
        results.append(result.id)
    
    return {
        "status": "batch_queued",
        "task_count": len(comment_list),
        "task_ids": results
    }