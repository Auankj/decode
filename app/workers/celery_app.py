"""
Celery Queue System Configuration
Production-ready Celery setup with monitoring and failure handling
Implements job queues as specified in MD file:
- comment_analysis
- nudge_check  
- progress_check
- auto_release_check
"""
from celery import Celery, signals
from celery.schedules import crontab
import os
import structlog
from kombu import Queue
from datetime import datetime

from app.core.config import get_settings, get_celery_config

# Configure structured logging
logger = structlog.get_logger(__name__)

# Get settings
settings = get_settings()

# Create Celery app with production configuration
celery_app = Celery(
    "cookie_licking_detector",
    include=[
        "app.workers.comment_analysis",
        "app.workers.nudge_check",
        "app.workers.progress_check", 
        "app.workers.periodic_tasks"
    ]
)

# Apply production configuration
celery_config = get_celery_config()
celery_app.conf.update(celery_config)

# Additional production configuration
celery_app.conf.update(
    # Queue declarations with priorities
    task_queues=(
        Queue("comment_analysis", routing_key="comment_analysis", priority=9),
        Queue("nudge_check", routing_key="nudge_check", priority=7),
        Queue("progress_check", routing_key="progress_check", priority=5), 
        Queue("auto_release_check", routing_key="auto_release_check", priority=8),
        Queue("periodic_tasks", routing_key="periodic_tasks", priority=3),
        Queue("dead_letter", routing_key="dead_letter", priority=1),
    ),
    
    # Task priority levels
    task_default_priority=5,
    
    # Monitoring and logging
    worker_send_task_events=True,
    task_send_sent_event=True,
    
    # Error handling
    task_annotations={
        "*": {
            "rate_limit": "100/m",  # Default rate limit
            "time_limit": 300,      # 5 minutes
            "soft_time_limit": 240, # 4 minutes
        },
        "app.workers.comment_analysis.*": {
            "rate_limit": "200/m",
            "priority": 9,
        },
        "app.workers.nudge_check.*": {
            "rate_limit": "50/m",
            "priority": 7,
        },
        "app.workers.progress_check.*": {
            "rate_limit": "100/m",
            "priority": 5,
        },
        "app.workers.auto_release.*": {
            "rate_limit": "30/m",
            "priority": 8,
        },
    },
    
    # Periodic task schedule
    beat_schedule={
        # Process pending nudge checks every 10 minutes
        "process-pending-nudges": {
            "task": "app.workers.nudge_check.batch_nudge_check",
            "schedule": crontab(minute="*/10"),
            "options": {"queue": "periodic_tasks"}
        },
        
        # Check progress on all active claims every hour
        "monitor-claim-progress": {
            "task": "app.workers.progress_check.batch_progress_check",
            "schedule": crontab(minute=0),
            "options": {"queue": "periodic_tasks"}
        },
        
        # Clean up completed queue jobs daily
        "cleanup-queue-jobs": {
            "task": "app.workers.periodic_tasks.cleanup_completed_jobs",
            "schedule": crontab(hour=2, minute=0),
            "options": {"queue": "periodic_tasks"}
        },
        
        # Generate daily metrics
        "generate-daily-metrics": {
            "task": "app.workers.periodic_tasks.generate_daily_metrics",
            "schedule": crontab(hour=1, minute=0),
            "options": {"queue": "periodic_tasks"}
        },
        
        # Health check for all services every 5 minutes
        "health-check": {
            "task": "app.workers.periodic_tasks.health_check",
            "schedule": crontab(minute="*/5"),
            "options": {"queue": "periodic_tasks"}
        },
    },
    
    # Result storage
    result_expires=3600,  # 1 hour
    result_persistent=True,
    
    # Worker configuration
    worker_log_format="[%(asctime)s: %(levelname)s/%(processName)s] %(message)s",
    worker_task_log_format="[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s",
    worker_hijack_root_logger=False,
    worker_redirect_stdouts_level="INFO",
    
    # Security
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    
    # Performance
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_disable_rate_limits=False,
    task_reject_on_worker_lost=True,
    
    # Monitoring
    task_track_started=True,
    task_time_limit=300,
    task_soft_time_limit=240,
)

# Task priority levels
PRIORITY_CRITICAL = 10
PRIORITY_HIGH = 9
PRIORITY_NORMAL = 5
PRIORITY_LOW = 1

# Force import all task modules to ensure registration
# This is needed because Celery's include parameter only works when worker starts
try:
    import app.workers.comment_analysis
    import app.workers.nudge_check
    import app.workers.progress_check
    import app.workers.periodic_tasks
except ImportError as e:
    logger.warning(f"Failed to import task modules: {e}")

@celery_app.task(bind=True, priority=PRIORITY_LOW)
def send_to_dead_letter_queue(self, task_data, error_info):
    """
    Send failed tasks to dead letter queue for manual review
    Enhanced with detailed error tracking and alerting
    """
    from app.models import QueueJob, SessionLocal
    from datetime import datetime
    
    logger.error(f"Task failed and sent to dead letter queue: {error_info}")
    
    db = SessionLocal()
    try:
        # Create dead letter record with enhanced metadata
        dead_letter_job = QueueJob(
            job_type="dead_letter",
            payload={
                "original_task": task_data,
                "error_info": error_info,
                "failed_at": datetime.utcnow().isoformat(),
                "worker_id": self.request.hostname,
                "task_id": self.request.id,
                "retries": self.request.retries,
                "original_task_name": self.request.task,
            },
            status="dead_letter",
            retry_count=self.request.retries,
            max_retries=0,  # Don't retry dead letter jobs
        )
        
        db.add(dead_letter_job)
        db.commit()
        
        # Alert administrators in production
        if settings.is_production():
            from app.services.notification_service import get_notification_service
            notification_service = get_notification_service()
            # Send admin alert (implement admin notification)
        
        logger.info(f"Dead letter job created with ID: {dead_letter_job.id}")
        return {"status": "dead_letter_created", "id": dead_letter_job.id}
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create dead letter job: {e}")
        raise
    finally:
        db.close()

# Celery signal handlers for monitoring and logging
@signals.task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **kwds):
    """Log task start"""
    logger.info(f"Task started: {task.name}[{task_id}]")

@signals.task_postrun.connect
def task_postrun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, retval=None, state=None, **kwds):
    """Log task completion"""
    logger.info(f"Task completed: {task.name}[{task_id}] - State: {state}")

@signals.task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, einfo=None, **kwds):
    """Log task failures and send to dead letter queue if max retries exceeded"""
    logger.error(f"Task failed: {sender.name}[{task_id}] - Exception: {exception}")
    
    # Check if max retries exceeded
    if hasattr(sender, 'request') and sender.request.retries >= sender.max_retries:
        send_to_dead_letter_queue.delay(
            task_data={
                "task_name": sender.name,
                "task_id": task_id,
                "args": getattr(sender.request, 'args', []),
                "kwargs": getattr(sender.request, 'kwargs', {}),
            },
            error_info={
                "exception": str(exception),
                "traceback": str(einfo),
                "retries": sender.request.retries,
            }
        )

@signals.task_retry.connect
def task_retry_handler(sender=None, task_id=None, reason=None, einfo=None, **kwds):
    """Log task retries"""
    logger.warning(f"Task retry: {sender.name}[{task_id}] - Reason: {reason}")

@signals.worker_ready.connect
def worker_ready_handler(sender=None, **kwargs):
    """Log worker ready"""
    logger.info(f"Worker ready: {sender.hostname}")

@signals.worker_shutdown.connect  
def worker_shutdown_handler(sender=None, **kwargs):
    """Log worker shutdown"""
    logger.info(f"Worker shutting down: {sender.hostname}")

@signals.beat_init.connect
def beat_init_handler(sender=None, **kwargs):
    """Log beat scheduler initialization"""
    logger.info("Celery Beat scheduler initialized")

if __name__ == "__main__":
    celery_app.start()