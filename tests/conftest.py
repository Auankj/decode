"""
Test configuration and fixtures for Cookie Licking Detector.
"""

import asyncio
import os
import pytest
from typing import AsyncGenerator, Generator
from unittest.mock import Mock, AsyncMock

import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
import redis.asyncio as redis

from app.main import app
from app.core.config import get_settings
from app.core.security import AuthenticationService, SecurityUtils, jwt_manager
from app.db.database import get_async_session, Base
from app.db.models.user import User, UserRole
from app.services.github_service import GitHubService
from app.services.notification_service import NotificationService


# Test database URL - use in-memory SQLite for fast tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Override settings for testing
test_settings = get_settings()
test_settings.DATABASE_URL = TEST_DATABASE_URL
test_settings.ENVIRONMENT = "testing"
test_settings.DEBUG = True
test_settings.ENABLE_METRICS = False


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def async_engine():
    """Create async database engine for testing."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False}
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def async_session(async_engine) -> AsyncSession:
    """Create async database session for testing."""
    async_session_maker = async_sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session_maker() as session:
        yield session


@pytest.fixture
def override_get_db(async_session):
    """Override database dependency for testing."""
    async def _override_get_db():
        yield async_session
    
    app.dependency_overrides[get_async_session] = _override_get_db
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client(override_get_db) -> TestClient:
    """Create FastAPI test client."""
    return TestClient(app)


@pytest.fixture
async def async_client(override_get_db) -> AsyncGenerator[AsyncClient, None]:
    """Create async HTTP client for testing."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
async def auth_service(async_session) -> AuthenticationService:
    """Create authentication service for testing."""
    return AuthenticationService(async_session)


@pytest.fixture
async def test_user(auth_service) -> User:
    """Create test user."""
    from app.core.security import UserCreate
    
    user_data = UserCreate(
        email="test@example.com",
        password="TestPassword123!",
        full_name="Test User",
        roles=[UserRole.USER]
    )
    
    return await auth_service.create_user(user_data)


@pytest.fixture
async def test_admin_user(auth_service) -> User:
    """Create test admin user."""
    from app.core.security import UserCreate
    
    user_data = UserCreate(
        email="admin@example.com",
        password="AdminPassword123!",
        full_name="Admin User",
        roles=[UserRole.ADMIN]
    )
    
    return await auth_service.create_user(user_data)


@pytest.fixture
async def test_maintainer_user(auth_service) -> User:
    """Create test maintainer user."""
    from app.core.security import UserCreate
    
    user_data = UserCreate(
        email="maintainer@example.com",
        password="MaintainerPassword123!",
        full_name="Maintainer User",
        roles=[UserRole.MAINTAINER]
    )
    
    return await auth_service.create_user(user_data)


@pytest.fixture
def user_token(test_user) -> str:
    """Create JWT token for test user."""
    return jwt_manager.create_token_pair(test_user).access_token


@pytest.fixture
def admin_token(test_admin_user) -> str:
    """Create JWT token for admin user."""
    return jwt_manager.create_token_pair(test_admin_user).access_token


@pytest.fixture
def maintainer_token(test_maintainer_user) -> str:
    """Create JWT token for maintainer user."""
    return jwt_manager.create_token_pair(test_maintainer_user).access_token


@pytest.fixture
async def test_api_key(auth_service, test_user) -> str:
    """Create test API key."""
    from app.core.security import APIKeyCreate
    
    key_data = APIKeyCreate(
        name="Test API Key",
        description="API key for testing",
        scopes=["repo:read", "claims:read"]
    )
    
    api_key_response = await auth_service.create_api_key(test_user.id, key_data)
    return api_key_response.key


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    mock_client = AsyncMock()
    mock_client.get.return_value = None
    mock_client.set.return_value = True
    mock_client.delete.return_value = True
    mock_client.ping.return_value = True
    mock_client.llen.return_value = 0
    return mock_client


@pytest.fixture
def mock_github_service():
    """Mock GitHub service."""
    mock_service = AsyncMock(spec=GitHubService)
    
    # Mock common methods
    mock_service.get_rate_limit.return_value = {
        "remaining": 5000,
        "limit": 5000,
        "reset_at": "2024-01-01T00:00:00Z"
    }
    
    mock_service.get_repository.return_value = {
        "id": 123456,
        "full_name": "owner/repo",
        "description": "Test repository",
        "language": "Python",
        "stargazers_count": 100,
        "forks_count": 20
    }
    
    mock_service.get_issues.return_value = [
        {
            "id": 1,
            "number": 101,
            "title": "Test Issue",
            "body": "This is a test issue",
            "state": "open",
            "user": {
                "login": "testuser",
                "id": 12345
            }
        }
    ]
    
    mock_service.get_issue_comments.return_value = [
        {
            "id": 1001,
            "body": "I'll take this issue!",
            "user": {
                "login": "contributor",
                "id": 54321
            },
            "created_at": "2024-01-01T12:00:00Z"
        }
    ]
    
    mock_service.assign_issue.return_value = True
    mock_service.unassign_issue.return_value = True
    mock_service.create_issue_comment.return_value = {
        "id": 2001,
        "body": "Comment created",
        "created_at": "2024-01-01T12:30:00Z"
    }
    
    return mock_service


@pytest.fixture
def mock_notification_service():
    """Mock notification service."""
    mock_service = AsyncMock(spec=NotificationService)
    
    mock_service.send_nudge_email.return_value = {
        "status": "sent",
        "message_id": "test_message_123"
    }
    
    mock_service.send_auto_release_email.return_value = {
        "status": "sent",
        "message_id": "test_message_456"
    }
    
    mock_service.send_maintainer_notification.return_value = {
        "status": "sent",
        "message_id": "test_message_789"
    }
    
    mock_service.post_github_comment.return_value = {
        "id": 3001,
        "body": "Automated comment",
        "created_at": "2024-01-01T13:00:00Z"
    }
    
    return mock_service


@pytest.fixture
async def test_repository(async_session):
    """Create test repository."""
    from app.db.models.repository import Repository
    
    repo = Repository(
        github_id=123456,
        full_name="owner/test-repo",
        name="test-repo",
        owner="owner",
        description="Test repository for cookie licking detection",
        language="Python",
        stars_count=100,
        forks_count=20,
        is_monitored=True,
        monitoring_settings={
            "grace_period_days": 7,
            "max_nudges": 2,
            "auto_release_enabled": True
        }
    )
    
    async_session.add(repo)
    await async_session.commit()
    await async_session.refresh(repo)
    
    return repo


@pytest.fixture
async def test_issue(async_session, test_repository):
    """Create test issue."""
    from app.db.models.issue import Issue
    
    issue = Issue(
        repository_id=test_repository.id,
        github_id=101,
        number=101,
        title="Test Issue for Cookie Licking",
        body="This is a test issue to detect cookie licking behavior",
        state="open",
        author_username="issueauthor",
        author_github_id=11111,
        labels=["bug", "help wanted"],
        created_at_github="2024-01-01T10:00:00Z",
        updated_at_github="2024-01-01T10:00:00Z"
    )
    
    async_session.add(issue)
    await async_session.commit()
    await async_session.refresh(issue)
    
    return issue


@pytest.fixture
async def test_claim(async_session, test_issue):
    """Create test claim."""
    from app.db.models.claim import Claim, ClaimStatus
    
    claim = Claim(
        issue_id=test_issue.id,
        username="testclaimer",
        github_user_id=22222,
        comment_body="I'll work on this issue!",
        comment_github_id=1001,
        confidence_score=95,
        status=ClaimStatus.ACTIVE,
        grace_period_end="2024-01-08T10:00:00Z"
    )
    
    async_session.add(claim)
    await async_session.commit()
    await async_session.refresh(claim)
    
    return claim


@pytest.fixture
def sample_github_comment():
    """Sample GitHub comment data."""
    return {
        "id": 1001,
        "body": "I'll take this issue and work on it!",
        "user": {
            "login": "contributor",
            "id": 54321,
            "avatar_url": "https://github.com/images/error/contributor.gif"
        },
        "created_at": "2024-01-01T12:00:00Z",
        "updated_at": "2024-01-01T12:00:00Z",
        "html_url": "https://github.com/owner/repo/issues/101#issuecomment-1001"
    }


@pytest.fixture
def sample_webhook_payload():
    """Sample GitHub webhook payload."""
    return {
        "action": "created",
        "issue": {
            "id": 101,
            "number": 101,
            "title": "Test Issue",
            "body": "This is a test issue",
            "state": "open",
            "user": {
                "login": "issueauthor",
                "id": 11111
            },
            "assignees": [],
            "labels": [
                {"name": "bug"},
                {"name": "help wanted"}
            ],
            "created_at": "2024-01-01T10:00:00Z",
            "updated_at": "2024-01-01T10:00:00Z"
        },
        "comment": {
            "id": 1001,
            "body": "I want to work on this issue!",
            "user": {
                "login": "contributor",
                "id": 54321
            },
            "created_at": "2024-01-01T12:00:00Z",
            "updated_at": "2024-01-01T12:00:00Z"
        },
        "repository": {
            "id": 123456,
            "full_name": "owner/test-repo",
            "name": "test-repo",
            "owner": {
                "login": "owner",
                "id": 99999
            },
            "description": "Test repository",
            "language": "Python"
        }
    }


# Pytest configuration
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", 
        "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers",
        "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers",
        "unit: mark test as unit test"
    )
    config.addinivalue_line(
        "markers",
        "api: mark test as API test"
    )


@pytest.fixture(autouse=True)
def cleanup_env():
    """Clean up environment variables after each test."""
    yield
    # Reset any environment variables that might have been set during tests
    test_env_vars = [
        "GITHUB_TOKEN",
        "SENDGRID_API_KEY", 
        "DATABASE_URL",
        "REDIS_URL"
    ]
    for var in test_env_vars:
        if var in os.environ:
            del os.environ[var]


@pytest.fixture
def mock_celery_task():
    """Mock Celery task for testing."""
    mock_task = Mock()
    mock_task.delay.return_value = Mock(id="test-task-id")
    mock_task.apply_async.return_value = Mock(id="test-task-id")
    return mock_task


class MockCeleryApp:
    """Mock Celery app for testing."""
    def __init__(self):
        self.tasks = {}
    
    def task(self, *args, **kwargs):
        def decorator(func):
            self.tasks[func.__name__] = func
            func.delay = Mock(return_value=Mock(id=f"mock-{func.__name__}"))
            func.apply_async = Mock(return_value=Mock(id=f"mock-{func.__name__}"))
            return func
        return decorator


@pytest.fixture
def mock_celery_app():
    """Mock Celery application."""
    return MockCeleryApp()


# Helper functions for tests
def create_auth_headers(token: str) -> dict:
    """Create authorization headers for API requests."""
    return {"Authorization": f"Bearer {token}"}


def create_api_key_headers(api_key: str) -> dict:
    """Create API key headers for requests."""
    return {"X-API-Key": api_key}


async def create_test_data(session: AsyncSession):
    """Create comprehensive test data."""
    # This can be used in integration tests that need complex scenarios
    pass