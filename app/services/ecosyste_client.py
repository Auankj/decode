"""
Ecosyste.ms API Client
As specified in MD file: 60 requests per minute, polite pool with email
"""
import httpx
import time
import asyncio
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import structlog
import os

logger = structlog.get_logger()

class EcosysteAPIClient:
    """
    Ecosyste.ms API client with rate limiting as specified in MD file:
    - 60 requests per minute per IP
    - Polite Pool with email parameter for better rate limits
    - Handles issues, comments, events data
    """
    
    def __init__(self):
        self.base_url = os.getenv("ECOSYSTE_MS_BASE_URL", "https://issues.ecosyste.ms/api/v1")
        self.email = os.getenv("ECOSYSTE_MS_EMAIL", "")
        self.client = httpx.AsyncClient(timeout=30.0)
        
        # Rate limiting: 60 requests per minute as per MD file
        self.rate_limit = 60  # requests per minute
        self.request_times = []
        
    async def _rate_limit_wait(self):
        """Implement 60 req/min rate limiting as specified in MD file"""
        now = time.time()
        # Remove requests older than 1 minute
        self.request_times = [t for t in self.request_times if now - t < 60]
        
        if len(self.request_times) >= self.rate_limit:
            # Wait until oldest request is 60 seconds old
            wait_time = 60 - (now - self.request_times[0])
            if wait_time > 0:
                logger.info(f"Rate limiting: waiting {wait_time:.2f} seconds")
                await asyncio.sleep(wait_time)
                
        self.request_times.append(now)
    
    async def _make_request(self, endpoint: str, params: Dict = None) -> Dict:
        """Make API request with rate limiting and error handling"""
        await self._rate_limit_wait()
        
        if params is None:
            params = {}
            
        # Use polite pool with email as specified in MD file
        if self.email:
            params['mailto'] = self.email
            
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"API request failed: {e}")
            raise
    
    async def get_repository_issues(
        self, 
        owner: str, 
        repo: str, 
        state: str = "open",
        per_page: int = 100
    ) -> List[Dict]:
        """Get issues for a repository with filters"""
        params = {
            "repository": f"{owner}/{repo}",
            "state": state,
            "per_page": per_page
        }
        
        response = await self._make_request("/issues", params)
        return response.get("data", [])
    
    async def get_issue_by_id(self, issue_id: int) -> Dict:
        """Get specific issue by ID"""
        response = await self._make_request(f"/issues/{issue_id}")
        return response
    
    async def get_issue_comments(self, issue_id: int) -> List[Dict]:
        """
        Get comments for a specific issue
        Essential for claim detection through comment pattern matching
        """
        response = await self._make_request(f"/issues/{issue_id}/comments")
        return response.get("data", [])
    
    async def get_issue_events(self, issue_id: int) -> List[Dict]:
        """Get timeline events for a specific issue"""
        response = await self._make_request(f"/issues/{issue_id}/events")
        return response.get("data", [])
    
    async def get_timeline_events(
        self, 
        repository: str = None, 
        event_type: str = None,
        since: datetime = None
    ) -> List[Dict]:
        """Get ecosystem-wide timeline events with filters"""
        params = {}
        if repository:
            params["repository"] = repository
        if event_type:
            params["type"] = event_type
        if since:
            params["since"] = since.isoformat()
            
        response = await self._make_request("/timeline", params)
        return response.get("data", [])
    
    async def get_user_commits(
        self, 
        owner: str, 
        repo: str, 
        username: str, 
        since: datetime = None
    ) -> List[Dict]:
        """Get commits by a specific user in a repository"""
        params = {
            "repository": f"{owner}/{repo}",
            "author": username
        }
        
        if since:
            params["since"] = since.isoformat()
            
        try:
            response = await self._make_request("/commits", params)
            return response.get("data", [])
        except Exception as e:
            logger.error(f"Error fetching commits for {username} in {owner}/{repo}: {e}")
            return []
    
    async def get_pull_requests(
        self,
        owner: str,
        repo: str, 
        state: str = "all",
        per_page: int = 100
    ) -> List[Dict]:
        """Get pull requests for a repository"""
        params = {
            "repository": f"{owner}/{repo}",
            "state": state,
            "per_page": per_page
        }
        
        try:
            response = await self._make_request("/pull_requests", params)
            return response.get("data", [])
        except Exception as e:
            logger.error(f"Error fetching PRs for {owner}/{repo}: {e}")
            return []
    
    async def get_pull_requests_by_user(
        self,
        owner: str,
        repo: str,
        username: str,
        since: datetime = None
    ) -> List[Dict]:
        """Get pull requests created by a specific user"""
        params = {
            "repository": f"{owner}/{repo}",
            "author": username
        }
        
        if since:
            params["since"] = since.isoformat()
            
        try:
            response = await self._make_request("/pull_requests", params)
            return response.get("data", [])
        except Exception as e:
            logger.error(f"Error fetching PRs by {username} in {owner}/{repo}: {e}")
            return []
    
    async def check_issue_pr_references(
        self,
        owner: str,
        repo: str,
        issue_number: int,
        username: str = None,
        since: datetime = None
    ) -> List[Dict]:
        """Check for PRs that reference a specific issue"""
        try:
            # Get all PRs for the repo since the specified date
            params = {"repository": f"{owner}/{repo}"}
            if since:
                params["since"] = since.isoformat()
            
            prs = await self.get_pull_requests(owner, repo)
            
            referenced_prs = []
            issue_patterns = [
                f"#{issue_number}",
                f"fix #{issue_number}",
                f"fixes #{issue_number}", 
                f"close #{issue_number}",
                f"closes #{issue_number}",
                f"resolve #{issue_number}",
                f"resolves #{issue_number}"
            ]
            
            for pr in prs:
                pr_body = (pr.get("body") or "").lower()
                pr_title = (pr.get("title") or "").lower()
                pr_text = f"{pr_title} {pr_body}"
                
                # Check if this PR references our issue
                if any(pattern.lower() in pr_text for pattern in issue_patterns):
                    # If username specified, only include PRs by that user
                    if not username or pr.get("user", {}).get("login") == username:
                        referenced_prs.append(pr)
            
            return referenced_prs
            
        except Exception as e:
            logger.error(f"Error checking PR references for issue #{issue_number} in {owner}/{repo}: {e}")
            return []
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

# Singleton instance
_client_instance = None

async def get_ecosyste_client() -> EcosysteAPIClient:
    """Get singleton Ecosyste.ms API client"""
    global _client_instance
    if _client_instance is None:
        _client_instance = EcosysteAPIClient()
    return _client_instance