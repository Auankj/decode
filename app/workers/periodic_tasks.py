"""
Periodic Tasks for System Maintenance and Monitoring
Implements background tasks for cleanup, metrics, and health checks
"""
from celery import Task
from datetime import datetime, timedelta
import structlog

from app.workers.celery_app import celery_app, PRIORITY_LOW
from app.models import SessionLocal, QueueJob, Claim, ActivityLog
from app.core.config import get_settings
from sqlalchemy import func, and_

logger = structlog.get_logger(__name__)
settings = get_settings()

class MaintenanceTask(Task):
    """Base task class for maintenance operations"""
    autoretry_for = (Exception,)
    retry_kwargs = {"max_retries": 3, "countdown": 300}
    retry_backoff = True

@celery_app.task(
    bind=True,
    base=MaintenanceTask,
    queue="periodic_tasks",
    priority=PRIORITY_LOW
)
def cleanup_completed_jobs(self):
    """
    Clean up completed queue jobs older than 7 days
    Keeps database lean and performant
    """
    
    db = SessionLocal()
    try:
        # Delete completed jobs older than 7 days
        cutoff_date = datetime.utcnow() - timedelta(days=7)
        
        deleted_count = db.query(QueueJob).filter(
            and_(
                QueueJob.status == "completed",
                QueueJob.processed_at < cutoff_date
            )
        ).delete()
        
        db.commit()
        
        logger.info(f"Cleaned up {deleted_count} completed queue jobs")
        return {"status": "success", "deleted_jobs": deleted_count}
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error during job cleanup: {e}")
        raise
    finally:
        db.close()

@celery_app.task(
    bind=True,
    base=MaintenanceTask,
    queue="periodic_tasks",
    priority=PRIORITY_LOW
)
def generate_daily_metrics(self):
    """
    Generate daily system metrics and store for reporting
    """
    
    db = SessionLocal()
    try:
        # Calculate metrics for the last 24 hours
        yesterday = datetime.utcnow() - timedelta(days=1)
        
        metrics = {
            "date": datetime.utcnow().date().isoformat(),
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        # Claim metrics
        total_claims = db.query(func.count(Claim.id)).scalar()
        active_claims = db.query(func.count(Claim.id)).filter(Claim.status == "active").scalar()
        new_claims_24h = db.query(func.count(Claim.id)).filter(Claim.created_at >= yesterday).scalar()
        
        metrics["claims"] = {
            "total": total_claims,
            "active": active_claims,
            "new_24h": new_claims_24h,
            "completed": db.query(func.count(Claim.id)).filter(Claim.status == "completed").scalar(),
            "released": db.query(func.count(Claim.id)).filter(Claim.status == "released").scalar(),
        }
        
        # Activity metrics
        activities_24h = db.query(func.count(ActivityLog.id)).filter(
            ActivityLog.timestamp >= yesterday
        ).scalar()
        
        nudges_sent_24h = db.query(func.count(ActivityLog.id)).filter(
            and_(
                ActivityLog.activity_type == "progress_nudge",
                ActivityLog.timestamp >= yesterday
            )
        ).scalar()
        
        auto_releases_24h = db.query(func.count(ActivityLog.id)).filter(
            and_(
                ActivityLog.activity_type == "auto_release",
                ActivityLog.timestamp >= yesterday
            )
        ).scalar()
        
        metrics["activity"] = {
            "total_24h": activities_24h,
            "nudges_sent_24h": nudges_sent_24h,
            "auto_releases_24h": auto_releases_24h,
        }
        
        # Queue metrics
        pending_jobs = db.query(func.count(QueueJob.id)).filter(QueueJob.status == "pending").scalar()
        failed_jobs = db.query(func.count(QueueJob.id)).filter(QueueJob.status == "failed").scalar()
        dead_letter_jobs = db.query(func.count(QueueJob.id)).filter(QueueJob.status == "dead_letter").scalar()
        
        metrics["queue"] = {
            "pending": pending_jobs,
            "failed": failed_jobs,
            "dead_letter": dead_letter_jobs,
        }
        
        # Performance metrics
        avg_claim_age = db.query(func.avg(
            func.extract('epoch', datetime.utcnow() - Claim.created_at) / 86400
        )).filter(Claim.status == "active").scalar()
        
        metrics["performance"] = {
            "avg_active_claim_age_days": float(avg_claim_age or 0)
        }
        
        logger.info(f"Daily metrics generated: {metrics}")
        
        # Store metrics in activity log for historical tracking
        metrics_log = ActivityLog(
            claim_id=None,  # System-wide metrics
            activity_type="daily_metrics",
            description="Daily system metrics generated",
            timestamp=datetime.utcnow(),
            metadata=metrics
        )
        db.add(metrics_log)
        db.commit()
        
        return metrics
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error generating daily metrics: {e}")
        raise
    finally:
        db.close()

@celery_app.task(
    bind=True,
    base=MaintenanceTask,
    queue="periodic_tasks",
    priority=PRIORITY_LOW
)
def health_check(self):
    """
    Comprehensive health check for all system components
    """
    
    health_status = {
        "timestamp": datetime.utcnow().isoformat(),
        "status": "healthy",
        "checks": {}
    }
    
    # Database connectivity check
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        
        # Check database performance
        claim_count = db.query(func.count(Claim.id)).scalar()
        db.close()
        
        health_status["checks"]["database"] = {
            "status": "healthy",
            "total_claims": claim_count
        }
    except Exception as e:
        health_status["checks"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "unhealthy"
    
    # Redis connectivity check
    try:
        import redis
        r = redis.from_url(settings.REDIS_URL)
        r.ping()
        
        # Check Redis memory usage
        info = r.info()
        used_memory_mb = info.get("used_memory", 0) / (1024 * 1024)
        
        health_status["checks"]["redis"] = {
            "status": "healthy",
            "used_memory_mb": round(used_memory_mb, 2)
        }
    except Exception as e:
        health_status["checks"]["redis"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "unhealthy"
    
    # GitHub API rate limit check
    try:
        from app.services.github_service import get_github_service
        github_service = get_github_service()
        rate_limit_status = github_service.get_rate_limit_status()
        
        # Check if rate limit is getting low
        core_remaining = rate_limit_status.get("core", {}).get("remaining", 0)
        if core_remaining < 100:
            health_status["checks"]["github_api"] = {
                "status": "degraded",
                "rate_limit": rate_limit_status,
                "warning": "GitHub API rate limit low"
            }
            health_status["status"] = "degraded"
        else:
            health_status["checks"]["github_api"] = {
                "status": "healthy",
                "rate_limit": rate_limit_status
            }
    except Exception as e:
        health_status["checks"]["github_api"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"  # GitHub issues shouldn't make system unhealthy
    
    # Ecosyste.ms API check
    try:
        import httpx
        with httpx.Client(timeout=10) as client:
            response = client.get(settings.ECOSYSTE_MS_BASE_URL)
            if response.status_code == 200:
                health_status["checks"]["ecosyste_ms_api"] = {
                    "status": "healthy",
                    "response_time_ms": response.elapsed.total_seconds() * 1000
                }
            else:
                health_status["checks"]["ecosyste_ms_api"] = {
                    "status": "degraded",
                    "http_status": response.status_code
                }
                if health_status["status"] == "healthy":
                    health_status["status"] = "degraded"
    except Exception as e:
        health_status["checks"]["ecosyste_ms_api"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        if health_status["status"] == "healthy":
            health_status["status"] = "degraded"
    
    # Queue health check
    try:
        db = SessionLocal()
        
        # Check for stuck jobs (pending for more than 1 hour)
        stuck_threshold = datetime.utcnow() - timedelta(hours=1)
        stuck_jobs = db.query(func.count(QueueJob.id)).filter(
            and_(
                QueueJob.status == "pending",
                QueueJob.scheduled_at < stuck_threshold
            )
        ).scalar()
        
        # Check dead letter queue size
        dead_letter_count = db.query(func.count(QueueJob.id)).filter(
            QueueJob.status == "dead_letter"
        ).scalar()
        
        if stuck_jobs > 10 or dead_letter_count > 50:
            health_status["checks"]["queues"] = {
                "status": "degraded",
                "stuck_jobs": stuck_jobs,
                "dead_letter_jobs": dead_letter_count,
                "warning": "High number of stuck or failed jobs"
            }
            if health_status["status"] == "healthy":
                health_status["status"] = "degraded"
        else:
            health_status["checks"]["queues"] = {
                "status": "healthy",
                "stuck_jobs": stuck_jobs,
                "dead_letter_jobs": dead_letter_count
            }
            
        db.close()
    except Exception as e:
        health_status["checks"]["queues"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "unhealthy"
    
    logger.info(f"Health check completed: {health_status['status']}")
    
    # Log health check results
    try:
        db = SessionLocal()
        health_log = ActivityLog(
            claim_id=None,
            activity_type="health_check",
            description=f"System health check: {health_status['status']}",
            timestamp=datetime.utcnow(),
            metadata=health_status
        )
        db.add(health_log)
        db.commit()
        db.close()
    except Exception as e:
        logger.error(f"Failed to log health check: {e}")
    
    return health_status

@celery_app.task(
    bind=True,
    base=MaintenanceTask,
    queue="periodic_tasks",
    priority=PRIORITY_LOW
)
def cleanup_old_activity_logs(self):
    """
    Clean up old activity logs to keep database size manageable
    Keep logs for 90 days by default
    """
    
    db = SessionLocal()
    try:
        # Delete activity logs older than 90 days (except system metrics)
        cutoff_date = datetime.utcnow() - timedelta(days=90)
        
        deleted_count = db.query(ActivityLog).filter(
            and_(
                ActivityLog.timestamp < cutoff_date,
                ActivityLog.activity_type != "daily_metrics",  # Keep metrics longer
                ActivityLog.activity_type != "health_check"    # Keep health checks longer
            )
        ).delete()
        
        db.commit()
        
        logger.info(f"Cleaned up {deleted_count} old activity logs")
        return {"status": "success", "deleted_logs": deleted_count}
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error during activity log cleanup: {e}")
        raise
    finally:
        db.close()

@celery_app.task(
    bind=True,
    base=MaintenanceTask,
    queue="periodic_tasks",
    priority=PRIORITY_LOW
)
def check_stale_claims(self):
    """
    Identify claims that may need attention
    Reports on claims that have been active too long
    """
    
    db = SessionLocal()
    try:
        # Find claims active for more than 2x the grace period
        grace_period_days = settings.DEFAULT_GRACE_PERIOD_DAYS
        stale_threshold = datetime.utcnow() - timedelta(days=grace_period_days * 2)
        
        stale_claims = db.query(Claim).filter(
            and_(
                Claim.status == "active",
                Claim.created_at < stale_threshold
            )
        ).all()
        
        stale_count = len(stale_claims)
        
        if stale_count > 0:
            logger.warning(f"Found {stale_count} stale claims requiring attention")
            
            # Log details about stale claims
            stale_details = []
            for claim in stale_claims:
                days_active = (datetime.utcnow() - claim.created_at).days
                stale_details.append({
                    "claim_id": claim.id,
                    "username": claim.github_username,
                    "issue_id": claim.issue_id,
                    "days_active": days_active,
                    "last_activity": claim.last_activity_timestamp.isoformat() if claim.last_activity_timestamp else None
                })
            
            # Store stale claims report
            stale_log = ActivityLog(
                claim_id=None,
                activity_type="stale_claims_report",
                description=f"Found {stale_count} stale claims",
                timestamp=datetime.utcnow(),
                metadata={
                    "stale_count": stale_count,
                    "threshold_days": grace_period_days * 2,
                    "claims": stale_details
                }
            )
            db.add(stale_log)
            db.commit()
        
        logger.info(f"Stale claims check completed: {stale_count} stale claims found")
        return {"status": "success", "stale_claims": stale_count}
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error during stale claims check: {e}")
        raise
    finally:
        db.close()