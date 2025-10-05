"""
Webhook handlers for Cookie Licking Detector.
Processes GitHub webhooks for issue comments and other events.
"""

import hashlib
import hmac
import json
from typing import Dict, Any

from fastapi import APIRouter, Request, HTTPException, status, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.monitoring import track_api_call
from app.db.database import get_async_session
from app.workers.comment_analysis import analyze_comment_for_claim
from app.tasks.progress_check import check_progress_task, update_progress_task
from app.db.models.repositories import Repository
from app.db.models.issues import Issue, IssueStatus
from app.db.models.claims import Claim, ClaimStatus
from sqlalchemy import select

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
logger = get_logger(__name__)
settings = get_settings()


def verify_github_signature(payload_body: bytes, signature_header: str) -> bool:
    """Verify GitHub webhook signature."""
    if not signature_header:
        return False
    
    try:
        hash_object = hmac.new(
            settings.GITHUB_WEBHOOK_SECRET.encode('utf-8'),
            msg=payload_body,
            digestmod=hashlib.sha256
        )
        expected_signature = f"sha256={hash_object.hexdigest()}"
        return hmac.compare_digest(expected_signature, signature_header)
    except Exception as e:
        logger.error(f"Signature verification failed: {e}")
        return False


@router.post("/github")
async def handle_github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_session)
):
    """Handle GitHub webhook events."""
    try:
        # Get headers
        github_event = request.headers.get("X-GitHub-Event")
        github_delivery = request.headers.get("X-GitHub-Delivery")
        signature_header = request.headers.get("X-Hub-Signature-256")
        
        # Get payload
        payload_body = await request.body()
        
        # Verify signature if webhook secret is configured
        if settings.GITHUB_WEBHOOK_SECRET and not verify_github_signature(payload_body, signature_header):
            track_api_call("webhook", "github", 401)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid signature"
            )
        
        # Parse JSON payload
        try:
            payload = json.loads(payload_body)
        except json.JSONDecodeError:
            track_api_call("webhook", "github", 400)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON payload"
            )
        
        logger.info(f"Received GitHub webhook: {github_event} - {github_delivery}")
        
        # Handle different event types
        if github_event == "issue_comment":
            await handle_issue_comment(payload, background_tasks, db)
        elif github_event == "issues":
            await handle_issues(payload, background_tasks, db)
        elif github_event == "pull_request":
            await handle_pull_request(payload, background_tasks, db)
        elif github_event == "push":
            await handle_push(payload, background_tasks, db)
        elif github_event == "ping":
            # Webhook test event
            track_api_call("webhook", "github_ping", 200)
            return {"message": "pong"}
        else:
            logger.info(f"Unhandled GitHub event: {github_event}")
        
        track_api_call("webhook", "github", 200)
        return {"message": "Webhook processed successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        track_api_call("webhook", "github", 500)
        logger.error(f"Webhook processing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook processing failed"
        )


async def handle_issue_comment(
    payload: Dict[str, Any],
    background_tasks: BackgroundTasks,
    db: AsyncSession
):
    """Handle issue comment events with complete pipeline."""
    action = payload.get("action")
    
    if action != "created":
        logger.debug(f"Ignoring issue comment action: {action}")
        return
    
    # Extract comment and issue data
    comment = payload.get("comment", {})
    issue = payload.get("issue", {})
    repository = payload.get("repository", {})
    
    # Check if repository is monitored or auto-create
    try:
        stmt = select(Repository).where(
            Repository.github_repo_id == repository.get("id")
        )
        result = await db.execute(stmt)
        repo_record = result.scalar_one_or_none()
        
        if not repo_record:
            # Auto-monitor new repository
            logger.info(f"Auto-monitoring new repository: {repository.get('full_name')}")
            
            from app.core.config import get_settings
            settings = get_settings()
            
            repo_record = Repository(
                github_repo_id=repository.get("id"),
                owner_name=repository.get("owner", {}).get("login", ""),
                name=repository.get("name", ""),
                full_name=repository.get("full_name", ""),
                url=repository.get("html_url", ""),
                is_monitored=True,  # Auto-enable monitoring
                grace_period_days=7,
                nudge_count=2,
                claim_detection_threshold=75,
                notification_settings={"enabled": True}
            )
            db.add(repo_record)
            await db.commit()
            await db.refresh(repo_record)
            
            logger.info(f"✅ Auto-added repository: {repo_record.full_name} (ID: {repo_record.id})")
        
        elif not repo_record.is_monitored:
            logger.info(f"Repository {repository.get('full_name')} not monitored, skipping")
            return
        
        # Get repository configuration
        repository_config = {
            "repository_id": repo_record.id,
            "grace_period_days": repo_record.grace_period_days,
            "nudge_count": repo_record.nudge_count,
            "claim_detection_threshold": repo_record.claim_detection_threshold,
            "notification_settings": repo_record.notification_settings or {}
        }
        
    except Exception as e:
        logger.error(f"Error checking repository config: {e}")
        # Use defaults if repo not found
        repository_config = {
            "repository_id": None,
            "grace_period_days": 7,
            "nudge_count": 2,
            "claim_detection_threshold": 75,
            "notification_settings": {}
        }
    
    # Prepare data for comment analysis
    comment_data = {
        "id": comment.get("id"),
        "body": comment.get("body", ""),
        "user": {
            "login": comment.get("user", {}).get("login"),
            "id": comment.get("user", {}).get("id")
        },
        "created_at": comment.get("created_at")
    }
    
    issue_data = {
        "id": issue.get("id"),
        "number": issue.get("number"),
        "title": issue.get("title", ""),
        "body": issue.get("body", ""),
        "state": issue.get("state"),
        "assignees": [assignee.get("login") for assignee in issue.get("assignees", [])]
    }
    
    # Find or create issue record in database
    try:
        if repository_config.get("repository_id"):
            stmt = select(Issue).where(
                Issue.repository_id == repository_config["repository_id"],
                Issue.github_issue_number == issue.get("number")
            )
            result = await db.execute(stmt)
            issue_record = result.scalar_one_or_none()
            
            if not issue_record:
                # Create issue record
                issue_record = Issue(
                    repository_id=repository_config["repository_id"],
                    github_repo_id=repository.get("id"),
                    github_issue_id=issue.get("id"),
                    github_issue_number=issue.get("number"),
                    title=issue.get("title", ""),
                    description=issue.get("body", ""),
                    status=IssueStatus.OPEN if issue.get("state") == "open" else IssueStatus.CLOSED,
                    github_data=issue
                )
                db.add(issue_record)
                await db.commit()
                await db.refresh(issue_record)
            issue_id = issue_record.id
        else:
            logger.warning("No repository_id found, cannot create issue record")
            return
        
    except Exception as e:
        logger.error(f"Error creating/finding issue record: {e}")
        await db.rollback()
        return
    
    # Queue comment analysis task
    from app.tasks.comment_analysis import analyze_comment_task
    
    # Prepare task data in the format expected by analyze_comment_task
    task_data = {
        'comment_id': comment_data['id'],
        'comment_body': comment_data['body'],
        'comment_url': f"https://github.com/{repository.get('full_name')}/issues/{issue.get('number')}#issuecomment-{comment_data['id']}",
        'comment_user': comment_data['user'],
        'issue_id': issue.get('id'),
        'issue_number': issue.get('number'),
        'issue_title': issue_data['title'],
        'repository_id': repository_config['repository_id'],
        'repository_full_name': repository.get('full_name'),
        'issue_data': issue_data
    }
    
    analyze_comment_task.delay(task_data)
    
    logger.info(f"Queued complete comment analysis for issue #{issue.get('number')} in {repository.get('full_name')}")


async def handle_issues(
    payload: Dict[str, Any],
    background_tasks: BackgroundTasks,
    db: AsyncSession
):
    """Handle issue events."""
    action = payload.get("action")
    
    if action in ["opened", "edited", "closed", "reopened", "assigned", "unassigned"]:
        issue = payload.get("issue", {})
        repository = payload.get("repository", {})
        
        issue_data = {
            "issue_id": issue.get("id"),
            "issue_number": issue.get("number"),
            "issue_title": issue.get("title", ""),
            "issue_body": issue.get("body", ""),
            "issue_state": issue.get("state"),
            "issue_assignees": [assignee.get("login") for assignee in issue.get("assignees", [])],
            "repository_id": repository.get("id"),
            "repository_full_name": repository.get("full_name"),
            "action": action
        }
        
        # If issue was assigned/unassigned, check for progress updates
        if action in ["assigned", "unassigned"]:
            check_progress_task.delay(issue_data)
        
        logger.info(f"Processed issue {action} for #{issue_data['issue_number']} in {issue_data['repository_full_name']}")


async def handle_pull_request(
    payload: Dict[str, Any],
    background_tasks: BackgroundTasks,
    db: AsyncSession
):
    """Handle pull request events."""
    action = payload.get("action")
    
    if action in ["opened", "closed", "merged"]:
        pull_request = payload.get("pull_request", {})
        repository = payload.get("repository", {})
        
        # Check if PR references any issues
        pr_body = pull_request.get("body", "")
        pr_title = pull_request.get("title", "")
        
        # Look for issue references (e.g., "fixes #123", "closes #456")
        import re
        issue_references = re.findall(
            r'(?:fix(?:es)?|close(?:s)?|resolve(?:s)?)\s+#(\d+)',
            f"{pr_title} {pr_body}",
            re.IGNORECASE
        )
        
        if issue_references:
            pr_data = {
                "pr_id": pull_request.get("id"),
                "pr_number": pull_request.get("number"),
                "pr_title": pr_title,
                "pr_state": pull_request.get("state"),
                "pr_merged": pull_request.get("merged", False),
                "pr_user": pull_request.get("user", {}).get("login"),
                "pr_user_id": pull_request.get("user", {}).get("id"),
                "repository_id": repository.get("id"),
                "repository_full_name": repository.get("full_name"),
                "referenced_issues": issue_references,
                "action": action
            }
            
            # Find claims for referenced issues and trigger progress checks
            try:
                from app.db.models import ClaimStatus
                
                for issue_number in issue_references:
                    # Find issue in database
                    stmt = select(Issue).where(
                        Issue.github_repo_id == repository.get("id"),
                        Issue.github_issue_number == int(issue_number)
                    )
                    result = await db.execute(stmt)
                    issue_record = result.scalar_one_or_none()
                    
                    if issue_record:
                        # Find active claims for this issue
                        stmt = select(Claim).where(
                            Claim.issue_id == issue_record.id,
                            Claim.status == ClaimStatus.ACTIVE
                        )
                        result = await db.execute(stmt)
                        active_claims = result.scalars().all()
                        
                        # Queue progress check for each active claim
                        for claim in active_claims:
                            # Update PR data for progress tracking
                            update_progress_task.delay(
                                claim_id=claim.id,
                                pr_data=pr_data
                            )
                            
                        logger.info(f"Queued progress checks for {len(active_claims)} claims on issue #{issue_number}")
            except Exception as e:
                logger.error(f"Error processing PR references: {e}")
            
            logger.info(f"PR #{pr_data['pr_number']} references issues: {issue_references}")


async def handle_push(
    payload: Dict[str, Any],
    background_tasks: BackgroundTasks,
    db: AsyncSession
):
    """Handle push events."""
    repository = payload.get("repository", {})
    commits = payload.get("commits", [])
    pusher = payload.get("pusher", {})
    
    # Check commits for issue references
    issue_references = []
    for commit in commits:
        message = commit.get("message", "")
        import re
        refs = re.findall(
            r'(?:fix(?:es)?|close(?:s)?|resolve(?:s)?)\s+#(\d+)',
            message,
            re.IGNORECASE
        )
        issue_references.extend(refs)
    
    if issue_references:
        push_data = {
            "repository_id": repository.get("id"),
            "repository_full_name": repository.get("full_name"),
            "pusher": pusher.get("name"),
            "commit_count": len(commits),
            "referenced_issues": list(set(issue_references)),  # Remove duplicates
            "ref": payload.get("ref")
        }
        
        # Queue progress check for referenced issues
        background_tasks.add_task(
            check_progress_task.delay,
            push_data
        )
        
        logger.info(f"Push to {push_data['repository_full_name']} references issues: {issue_references}")


@router.post("/test")
async def test_webhook(
    request: Request,
    background_tasks: BackgroundTasks
):
    """Test webhook endpoint for development."""
    if settings.ENVIRONMENT != "development":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not found"
        )
    
    payload = await request.json()
    
    logger.info("Test webhook received")
    logger.debug(f"Test payload: {payload}")
    
    track_api_call("webhook", "test", 200)
    return {"message": "Test webhook processed", "payload": payload}


@router.get("/health")
async def webhook_health():
    """Webhook service health check."""
    track_api_call("webhook", "health", 200)
    return {
        "status": "healthy",
        "service": "webhooks",
        "webhook_secret_configured": bool(settings.GITHUB_WEBHOOK_SECRET)
    }