"""
GitHub API Service
Production-ready GitHub integration with full authentication and operations
No placeholders - fully functional GitHub API client
"""
import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import structlog
import httpx
from github import Github, Auth
from github.GithubException import GithubException, RateLimitExceededException

from app.core.config import get_settings

logger = structlog.get_logger(__name__)

class GitHubAPIService:
    """
    Production GitHub API service with rate limiting and error handling
    Implements all operations specified in MD file
    """
    
    def __init__(self):
        settings = get_settings()
        
        # Initialize with GitHub token or graceful fallback
        self.github = None
        self.authenticated = False
        
        if settings.GITHUB_TOKEN:
            try:
                auth = Auth.Token(settings.GITHUB_TOKEN)
                self.github = Github(auth=auth)
                self.authenticated = True
                logger.info("GitHub service initialized with token authentication")
            except Exception as e:
                logger.warning(f"Failed to initialize GitHub with token: {e}")
        elif settings.GITHUB_APP_ID and settings.GITHUB_APP_PRIVATE_KEY_PATH:
            try:
                auth = Auth.AppAuth(
                    settings.GITHUB_APP_ID,
                    settings.GITHUB_APP_PRIVATE_KEY_PATH
                )
                self.github = Github(auth=auth)
                self.authenticated = True
                logger.info("GitHub service initialized with App authentication")
            except Exception as e:
                logger.warning(f"Failed to initialize GitHub with App auth: {e}")
        
        if not self.authenticated:
            logger.warning("GitHub service running without authentication - API calls will be limited")
            self.github = Github()  # Public API only
        
        # HTTP client for webhook verification and raw API calls
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Cookie-Licking-Detector/1.0"
        }
        
        # Only add auth header if we have a token
        if settings.GITHUB_TOKEN:
            headers["Authorization"] = f"token {settings.GITHUB_TOKEN}"
            
        self.http_client = httpx.AsyncClient(
            timeout=30.0,
            headers=headers
        )
        
        # Rate limiting tracking
        self.rate_limit_remaining = 5000
        self.rate_limit_reset = time.time() + 3600
        self.secondary_rate_limit_remaining = 1000
        
    async def get_repository(self, owner: str, name: str) -> Dict[str, Any]:
        """Get repository information from GitHub"""
        
        if not self.github:
            raise ValueError("GitHub service not properly initialized")
        
        try:
            await self._check_rate_limit()
            
            repo = self.github.get_repo(f"{owner}/{name}")
            
            return {
                "id": repo.id,
                "name": repo.name,
                "full_name": repo.full_name,
                "owner": {
                    "login": repo.owner.login,
                    "id": repo.owner.id,
                    "type": repo.owner.type
                },
                "private": repo.private,
                "html_url": repo.html_url,
                "description": repo.description,
                "language": repo.language,
                "stargazers_count": repo.stargazers_count,
                "forks_count": repo.forks_count,
                "open_issues_count": repo.open_issues_count,
                "created_at": repo.created_at.isoformat() if repo.created_at else None,
                "updated_at": repo.updated_at.isoformat() if repo.updated_at else None,
                "permissions": {
                    "admin": repo.permissions.admin if hasattr(repo.permissions, 'admin') else False,
                    "maintain": repo.permissions.maintain if hasattr(repo.permissions, 'maintain') else False,
                    "push": repo.permissions.push if hasattr(repo.permissions, 'push') else False,
                    "pull": repo.permissions.pull if hasattr(repo.permissions, 'pull') else False
                }
            }
            
        except GithubException as e:
            if e.status == 401:
                logger.error(f"Authentication failed for repository {owner}/{name}")
                raise ValueError("GitHub authentication required for this operation")
            elif e.status == 403:
                logger.error(f"Access denied for repository {owner}/{name}")
                raise ValueError("Insufficient permissions to access this repository")
            elif e.status == 404:
                logger.warning(f"Repository {owner}/{name} not found")
                raise ValueError(f"Repository {owner}/{name} not found")
            logger.error(f"GitHub API error getting repository {owner}/{name}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting repository {owner}/{name}: {e}")
            raise

    async def get_issue(self, owner: str, name: str, issue_number: int) -> Dict[str, Any]:
        """Get specific issue from GitHub"""
        
        if not self.github:
            raise ValueError("GitHub service not properly initialized")
        
        try:
            await self._check_rate_limit()
            
            repo = self.github.get_repo(f"{owner}/{name}")
            issue = repo.get_issue(issue_number)
            
            return {
                "id": issue.id,
                "number": issue.number,
                "title": issue.title,
                "body": issue.body,
                "state": issue.state,
                "user": {
                    "login": issue.user.login,
                    "id": issue.user.id
                },
                "assignees": [
                    {
                        "login": assignee.login,
                        "id": assignee.id
                    } for assignee in issue.assignees
                ],
                "labels": [
                    {
                        "name": label.name,
                        "color": label.color
                    } for label in issue.labels
                ],
                "created_at": issue.created_at.isoformat(),
                "updated_at": issue.updated_at.isoformat(),
                "closed_at": issue.closed_at.isoformat() if issue.closed_at else None,
                "html_url": issue.html_url,
                "comments": issue.comments,
                "repository": {
                    "full_name": repo.full_name,
                    "owner": repo.owner.login
                }
            }
            
        except GithubException as e:
            if e.status == 401:
                logger.error(f"Authentication failed for issue {owner}/{name}#{issue_number}")
                raise ValueError("GitHub authentication required for this operation")
            elif e.status == 403:
                logger.error(f"Access denied for issue {owner}/{name}#{issue_number}")
                raise ValueError("Insufficient permissions to access this issue")
            elif e.status == 404:
                logger.warning(f"Issue {owner}/{name}#{issue_number} not found")
                raise ValueError(f"Issue {owner}/{name}#{issue_number} not found")
            logger.error(f"GitHub API error getting issue {owner}/{name}#{issue_number}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting issue {owner}/{name}#{issue_number}: {e}")
            raise

    async def get_issue_comments(self, owner: str, name: str, issue_number: int) -> List[Dict[str, Any]]:
        """Get comments for a specific issue"""
        
        try:
            await self._check_rate_limit()
            
            repo = self.github.get_repo(f"{owner}/{name}")
            issue = repo.get_issue(issue_number)
            comments = issue.get_comments()
            
            comment_list = []
            for comment in comments:
                comment_list.append({
                    "id": comment.id,
                    "body": comment.body,
                    "user": {
                        "login": comment.user.login,
                        "id": comment.user.id
                    },
                    "created_at": comment.created_at.isoformat(),
                    "updated_at": comment.updated_at.isoformat(),
                    "html_url": comment.html_url
                })
            
            return comment_list
            
        except GithubException as e:
            logger.error(f"GitHub API error getting comments for {owner}/{name}#{issue_number}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting comments for {owner}/{name}#{issue_number}: {e}")
            raise

    async def post_issue_comment(self, owner: str, name: str, issue_number: int, body: str) -> Dict[str, Any]:
        """Post a comment on an issue"""
        
        if not self.github:
            raise ValueError("GitHub service not properly initialized")
        
        if not self.authenticated:
            raise ValueError("GitHub authentication required to post comments")
        
        try:
            await self._check_rate_limit()
            
            repo = self.github.get_repo(f"{owner}/{name}")
            issue = repo.get_issue(issue_number)
            comment = issue.create_comment(body)
            
            logger.info(f"Posted comment on issue {owner}/{name}#{issue_number}")
            
            return {
                "id": comment.id,
                "body": comment.body,
                "html_url": comment.html_url,
                "created_at": comment.created_at.isoformat()
            }
            
        except GithubException as e:
            logger.error(f"GitHub API error posting comment to {owner}/{name}#{issue_number}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error posting comment to {owner}/{name}#{issue_number}: {e}")
            raise

    async def assign_issue(self, owner: str, name: str, issue_number: int, assignees: List[str]) -> bool:
        """Assign users to an issue"""
        
        if not self.github:
            raise ValueError("GitHub service not properly initialized")
        
        if not self.authenticated:
            logger.error("GitHub authentication required to assign issues")
            return False
        
        try:
            await self._check_rate_limit()
            
            repo = self.github.get_repo(f"{owner}/{name}")
            issue = repo.get_issue(issue_number)
            
            # Get user objects
            user_objects = []
            for username in assignees:
                try:
                    user = self.github.get_user(username)
                    user_objects.append(user)
                except GithubException as e:
                    logger.warning(f"Could not find user {username}: {e}")
                    continue
            
            if user_objects:
                issue.edit(assignees=user_objects)
                logger.info(f"Assigned {assignees} to issue {owner}/{name}#{issue_number}")
                return True
            else:
                logger.warning(f"No valid assignees found for {owner}/{name}#{issue_number}")
                return False
                
        except GithubException as e:
            logger.error(f"GitHub API error assigning issue {owner}/{name}#{issue_number}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error assigning issue {owner}/{name}#{issue_number}: {e}")
            return False

    async def unassign_issue(self, owner: str, name: str, issue_number: int, username: str) -> bool:
        """Remove user assignment from an issue"""
        
        try:
            await self._check_rate_limit()
            
            repo = self.github.get_repo(f"{owner}/{name}")
            issue = repo.get_issue(issue_number)
            
            # Get current assignees
            current_assignees = [assignee for assignee in issue.assignees 
                               if assignee.login != username]
            
            issue.edit(assignees=current_assignees)
            logger.info(f"Unassigned {username} from issue {owner}/{name}#{issue_number}")
            return True
                
        except GithubException as e:
            logger.error(f"GitHub API error unassigning issue {owner}/{name}#{issue_number}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error unassigning issue {owner}/{name}#{issue_number}: {e}")
            return False

    async def get_pull_requests_for_issue(self, owner: str, name: str, issue_number: int) -> List[Dict[str, Any]]:
        """Get pull requests that reference an issue"""
        
        try:
            await self._check_rate_limit()
            
            repo = self.github.get_repo(f"{owner}/{name}")
            
            # Search for PRs that reference this issue
            query = f"repo:{owner}/{name} is:pr #{issue_number}"
            search_result = self.github.search_issues(query)
            
            prs = []
            for pr in search_result:
                if pr.pull_request:
                    pr_data = repo.get_pull(pr.number)
                    prs.append({
                        "id": pr_data.id,
                        "number": pr_data.number,
                        "title": pr_data.title,
                        "state": pr_data.state,
                        "user": {
                            "login": pr_data.user.login,
                            "id": pr_data.user.id
                        },
                        "created_at": pr_data.created_at.isoformat(),
                        "updated_at": pr_data.updated_at.isoformat(),
                        "merged_at": pr_data.merged_at.isoformat() if pr_data.merged_at else None,
                        "html_url": pr_data.html_url,
                        "commits": pr_data.commits
                    })
            
            return prs
            
        except GithubException as e:
            logger.error(f"GitHub API error getting PRs for issue {owner}/{name}#{issue_number}: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error getting PRs for issue {owner}/{name}#{issue_number}: {e}")
            return []

    async def get_user_commits(self, owner: str, name: str, username: str, since: datetime) -> List[Dict[str, Any]]:
        """Get commits by a user in a repository since a specific date"""
        
        try:
            await self._check_rate_limit()
            
            repo = self.github.get_repo(f"{owner}/{name}")
            commits = repo.get_commits(author=username, since=since)
            
            commit_list = []
            for commit in commits:
                commit_list.append({
                    "sha": commit.sha,
                    "message": commit.commit.message,
                    "author": {
                        "name": commit.commit.author.name,
                        "email": commit.commit.author.email,
                        "date": commit.commit.author.date.isoformat()
                    },
                    "html_url": commit.html_url,
                    "stats": {
                        "additions": commit.stats.additions if commit.stats else 0,
                        "deletions": commit.stats.deletions if commit.stats else 0,
                        "total": commit.stats.total if commit.stats else 0
                    }
                })
            
            return commit_list
            
        except GithubException as e:
            logger.error(f"GitHub API error getting commits for {username} in {owner}/{name}: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error getting commits for {username} in {owner}/{name}: {e}")
            return []

    async def create_webhook(self, owner: str, name: str, webhook_url: str, secret: str) -> Dict[str, Any]:
        """Create a webhook for repository events"""
        
        if not self.github:
            raise ValueError("GitHub service not properly initialized")
        
        if not self.authenticated:
            raise ValueError("GitHub authentication required to create webhooks")
        
        try:
            await self._check_rate_limit()
            
            repo = self.github.get_repo(f"{owner}/{name}")
            
            config = {
                "url": webhook_url,
                "content_type": "json",
                "secret": secret
            }
            
            events = [
                "issues",
                "issue_comment",
                "pull_request",
                "push"
            ]
            
            hook = repo.create_hook("web", config, events)
            
            logger.info(f"Created webhook for repository {owner}/{name}")
            
            return {
                "id": hook.id,
                "name": hook.name,
                "config": hook.config,
                "events": hook.events,
                "active": hook.active,
                "created_at": hook.created_at.isoformat(),
                "updated_at": hook.updated_at.isoformat()
            }
            
        except GithubException as e:
            logger.error(f"GitHub API error creating webhook for {owner}/{name}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating webhook for {owner}/{name}: {e}")
            raise

    async def verify_webhook_signature(self, payload: bytes, signature: str, secret: str) -> bool:
        """Verify GitHub webhook signature"""
        
        import hmac
        import hashlib
        
        if not signature:
            return False
        
        try:
            # GitHub sends signature as 'sha1=<signature>'
            expected_signature = hmac.new(
                secret.encode('utf-8'),
                payload,
                hashlib.sha1
            ).hexdigest()
            
            signature = signature.replace('sha1=', '')
            
            return hmac.compare_digest(signature, expected_signature)
            
        except Exception as e:
            logger.error(f"Error verifying webhook signature: {e}")
            return False

    async def _check_rate_limit(self):
        """Check and handle GitHub API rate limiting"""
        
        try:
            rate_limit = self.github.get_rate_limit()
            
            # Core API rate limit
            if rate_limit.core.remaining < 100:
                reset_time = rate_limit.core.reset.timestamp()
                current_time = time.time()
                
                if reset_time > current_time:
                    sleep_time = reset_time - current_time + 10  # Add 10 second buffer
                    logger.warning(f"Approaching GitHub API rate limit. Sleeping for {sleep_time} seconds")
                    await asyncio.sleep(sleep_time)
            
            self.rate_limit_remaining = rate_limit.core.remaining
            self.rate_limit_reset = rate_limit.core.reset.timestamp()
            
        except RateLimitExceededException as e:
            logger.error(f"GitHub API rate limit exceeded: {e}")
            # Wait until rate limit resets
            await asyncio.sleep(3600)  # Wait 1 hour
            raise
        except Exception as e:
            logger.warning(f"Could not check rate limit: {e}")

    def get_rate_limit_status(self) -> Dict[str, Any]:
        """Get current rate limit status"""
        
        try:
            rate_limit = self.github.get_rate_limit()
            
            return {
                "core": {
                    "limit": rate_limit.core.limit,
                    "remaining": rate_limit.core.remaining,
                    "reset": rate_limit.core.reset.isoformat(),
                    "used": rate_limit.core.used
                },
                "search": {
                    "limit": rate_limit.search.limit,
                    "remaining": rate_limit.search.remaining,
                    "reset": rate_limit.search.reset.isoformat(),
                    "used": rate_limit.search.used
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting rate limit status: {e}")
            return {
                "core": {"limit": 5000, "remaining": 0, "used": 5000},
                "search": {"limit": 30, "remaining": 0, "used": 30}
            }

    async def close(self):
        """Close HTTP client"""
        await self.http_client.aclose()

# Global GitHub service instance
_github_service = None

def get_github_service() -> GitHubAPIService:
    """Get singleton GitHub service instance"""
    global _github_service
    if _github_service is None:
        _github_service = GitHubAPIService()
    return _github_service

# Convenience functions for use in workers
async def post_issue_comment(issue, message: str) -> bool:
    """Post comment on issue"""
    
    if not issue or not issue.repository:
        return False
        
    try:
        github_service = get_github_service()
        await github_service.post_issue_comment(
            owner=issue.repository.owner,
            name=issue.repository.name, 
            issue_number=issue.github_issue_number,
            body=message
        )
        return True
    except Exception as e:
        logger.error(f"Failed to post comment on issue {issue.id}: {e}")
        return False

async def remove_issue_assignee(claim) -> bool:
    """Remove assignee from issue"""
    
    if not claim or not claim.issue or not claim.issue.repository:
        return False
        
    try:
        github_service = get_github_service()
        await github_service.unassign_issue(
            owner=claim.issue.repository.owner,
            name=claim.issue.repository.name,
            issue_number=claim.issue.github_issue_number,
            username=claim.github_username
        )
        return True
    except Exception as e:
        logger.error(f"Failed to remove assignee from issue {claim.issue_id}: {e}")
        return False

async def post_maintainer_notification(issue, message: str) -> bool:
    """Post maintainer notification comment"""
    
    return await post_issue_comment(issue, message)