"""
Unit tests for authentication and security functionality.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch

from app.core.security import (
    SecurityUtils, JWTManager, AuthenticationService,
    UserCreate, UserLogin, APIKeyCreate,
    validate_email, validate_url
)
from app.db.models.user import UserRole


@pytest.mark.unit
class TestSecurityUtils:
    """Test security utility functions."""
    
    def test_hash_password(self):
        """Test password hashing."""
        password = "TestPassword123!"
        hashed = SecurityUtils.hash_password(password)
        
        assert hashed != password
        assert len(hashed) > 0
        assert hashed.startswith('$2b$')
    
    def test_verify_password_success(self):
        """Test successful password verification."""
        password = "TestPassword123!"
        hashed = SecurityUtils.hash_password(password)
        
        assert SecurityUtils.verify_password(password, hashed) is True
    
    def test_verify_password_failure(self):
        """Test failed password verification."""
        password = "TestPassword123!"
        wrong_password = "WrongPassword123!"
        hashed = SecurityUtils.hash_password(password)
        
        assert SecurityUtils.verify_password(wrong_password, hashed) is False
    
    def test_verify_password_invalid_hash(self):
        """Test password verification with invalid hash."""
        password = "TestPassword123!"
        invalid_hash = "invalid_hash"
        
        assert SecurityUtils.verify_password(password, invalid_hash) is False
    
    def test_generate_api_key(self):
        """Test API key generation."""
        api_key = SecurityUtils.generate_api_key()
        
        assert api_key.startswith("ckd_")
        assert len(api_key) > 20
        
        # Generate another key to ensure uniqueness
        another_key = SecurityUtils.generate_api_key()
        assert api_key != another_key
    
    def test_hash_api_key(self):
        """Test API key hashing."""
        api_key = "ckd_test_key_123"
        hashed = SecurityUtils.hash_api_key(api_key)
        
        assert hashed != api_key
        assert len(hashed) == 64  # SHA256 hex digest length
        
        # Same input should produce same hash
        assert SecurityUtils.hash_api_key(api_key) == hashed
    
    def test_generate_token_secret(self):
        """Test token secret generation."""
        secret = SecurityUtils.generate_token_secret()
        
        assert len(secret) > 20
        assert isinstance(secret, str)
        
        # Generate another secret to ensure uniqueness
        another_secret = SecurityUtils.generate_token_secret()
        assert secret != another_secret
    
    def test_sanitize_input(self):
        """Test input sanitization."""
        # Normal input
        clean_input = "This is a normal string"
        assert SecurityUtils.sanitize_input(clean_input) == clean_input
        
        # Input with dangerous patterns
        dangerous_input = "<script>alert('xss')</script>Hello world"
        sanitized = SecurityUtils.sanitize_input(dangerous_input)
        assert "<script>" not in sanitized
        assert "Hello world" in sanitized
        
        # Long input
        long_input = "A" * 2000
        sanitized = SecurityUtils.sanitize_input(long_input, max_length=100)
        assert len(sanitized) == 100
        
        # Empty input
        assert SecurityUtils.sanitize_input("") == ""
        assert SecurityUtils.sanitize_input(None) == ""
    
    def test_validate_password_strength(self):
        """Test password strength validation."""
        # Strong password
        strong_password = "StrongPassword123!"
        result = SecurityUtils.validate_password_strength(strong_password)
        assert result["is_valid"] is True
        assert len(result["errors"]) == 0
        
        # Weak passwords
        weak_passwords = [
            "short",  # Too short
            "alllowercase123!",  # No uppercase
            "ALLUPPERCASE123!",  # No lowercase
            "NoNumbers!",  # No numbers
            "NoSpecialChars123",  # No special characters
        ]
        
        for weak_password in weak_passwords:
            result = SecurityUtils.validate_password_strength(weak_password)
            assert result["is_valid"] is False
            assert len(result["errors"]) > 0


@pytest.mark.unit
class TestJWTManager:
    """Test JWT token management."""
    
    def setup_method(self):
        """Set up test method."""
        self.jwt_manager = JWTManager()
    
    def test_create_access_token(self):
        """Test access token creation."""
        token_data = {
            "sub": 123,
            "email": "test@example.com",
            "roles": ["user"]
        }
        
        token = self.jwt_manager.create_access_token(token_data)
        
        assert isinstance(token, str)
        assert len(token) > 50  # JWT tokens are quite long
        assert "." in token  # JWT tokens have dots as separators
    
    def test_create_refresh_token(self):
        """Test refresh token creation."""
        token_data = {
            "sub": 123,
            "email": "test@example.com",
            "roles": ["user"]
        }
        
        token = self.jwt_manager.create_refresh_token(token_data)
        
        assert isinstance(token, str)
        assert len(token) > 50
        assert "." in token
    
    def test_verify_token_success(self):
        """Test successful token verification."""
        token_data = {
            "sub": 123,
            "email": "test@example.com",
            "roles": ["user"]
        }
        
        token = self.jwt_manager.create_access_token(token_data)
        decoded_data = self.jwt_manager.verify_token(token)
        
        assert decoded_data.user_id == 123
        assert decoded_data.email == "test@example.com"
        assert decoded_data.roles == ["user"]
        assert decoded_data.token_type == "access"
    
    def test_verify_token_invalid(self):
        """Test token verification with invalid token."""
        invalid_token = "invalid.token.here"
        
        with pytest.raises(Exception):  # Should raise HTTPException
            self.jwt_manager.verify_token(invalid_token)
    
    def test_verify_token_missing_user_id(self):
        """Test token verification with missing user ID."""
        # Create token without user ID
        from jose import jwt
        import time
        
        payload = {
            "email": "test@example.com",
            "exp": time.time() + 3600
        }
        
        token = jwt.encode(payload, self.jwt_manager.secret_key, algorithm=self.jwt_manager.algorithm)
        
        with pytest.raises(Exception):  # Should raise HTTPException
            self.jwt_manager.verify_token(token)
    
    @patch('app.core.security.datetime')
    def test_create_token_pair(self, mock_datetime):
        """Test token pair creation."""
        # Mock datetime to have consistent results
        mock_now = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now
        
        # Create mock user
        mock_user = Mock()
        mock_user.id = 123
        mock_user.email = "test@example.com"
        mock_user.roles = [UserRole.USER]
        
        token_pair = self.jwt_manager.create_token_pair(mock_user)
        
        assert hasattr(token_pair, 'access_token')
        assert hasattr(token_pair, 'refresh_token')
        assert hasattr(token_pair, 'token_type')
        assert hasattr(token_pair, 'expires_in')
        assert token_pair.token_type == "bearer"
        assert token_pair.expires_in > 0


@pytest.mark.unit
@pytest.mark.asyncio
class TestAuthenticationService:
    """Test authentication service."""
    
    async def test_create_user_success(self, async_session):
        """Test successful user creation."""
        auth_service = AuthenticationService(async_session)
        
        user_data = UserCreate(
            email="newuser@example.com",
            password="StrongPassword123!",
            full_name="New User",
            roles=[UserRole.USER]
        )
        
        user = await auth_service.create_user(user_data)
        
        assert user.email == "newuser@example.com"
        assert user.full_name == "New User"
        assert user.is_active is True
        assert UserRole.USER in user.roles
        assert user.password_hash != "StrongPassword123!"  # Should be hashed
    
    async def test_create_user_weak_password(self, async_session):
        """Test user creation with weak password."""
        auth_service = AuthenticationService(async_session)
        
        user_data = UserCreate(
            email="newuser@example.com",
            password="weak",  # Weak password
            full_name="New User"
        )
        
        with pytest.raises(Exception):  # Should raise HTTPException
            await auth_service.create_user(user_data)
    
    async def test_create_user_duplicate_email(self, async_session, test_user):
        """Test user creation with duplicate email."""
        auth_service = AuthenticationService(async_session)
        
        user_data = UserCreate(
            email=test_user.email,  # Same email as existing user
            password="StrongPassword123!",
            full_name="Duplicate User"
        )
        
        with pytest.raises(Exception):  # Should raise HTTPException
            await auth_service.create_user(user_data)
    
    async def test_authenticate_user_success(self, async_session, test_user):
        """Test successful user authentication."""
        auth_service = AuthenticationService(async_session)
        
        authenticated_user = await auth_service.authenticate_user(
            test_user.email, 
            "TestPassword123!"
        )
        
        assert authenticated_user is not None
        assert authenticated_user.id == test_user.id
        assert authenticated_user.email == test_user.email
    
    async def test_authenticate_user_wrong_password(self, async_session, test_user):
        """Test authentication with wrong password."""
        auth_service = AuthenticationService(async_session)
        
        authenticated_user = await auth_service.authenticate_user(
            test_user.email,
            "WrongPassword123!"
        )
        
        assert authenticated_user is None
    
    async def test_authenticate_user_nonexistent(self, async_session):
        """Test authentication with nonexistent user."""
        auth_service = AuthenticationService(async_session)
        
        authenticated_user = await auth_service.authenticate_user(
            "nonexistent@example.com",
            "AnyPassword123!"
        )
        
        assert authenticated_user is None
    
    async def test_get_user_by_id_success(self, async_session, test_user):
        """Test successful user retrieval by ID."""
        auth_service = AuthenticationService(async_session)
        
        retrieved_user = await auth_service.get_user_by_id(test_user.id)
        
        assert retrieved_user is not None
        assert retrieved_user.id == test_user.id
        assert retrieved_user.email == test_user.email
    
    async def test_get_user_by_id_nonexistent(self, async_session):
        """Test user retrieval with nonexistent ID."""
        auth_service = AuthenticationService(async_session)
        
        retrieved_user = await auth_service.get_user_by_id(99999)
        
        assert retrieved_user is None
    
    async def test_create_api_key_success(self, async_session, test_user):
        """Test successful API key creation."""
        auth_service = AuthenticationService(async_session)
        
        key_data = APIKeyCreate(
            name="Test API Key",
            description="API key for testing",
            scopes=["repo:read", "claims:read"]
        )
        
        api_key_response = await auth_service.create_api_key(test_user.id, key_data)
        
        assert api_key_response.name == "Test API Key"
        assert api_key_response.key.startswith("ckd_")
        assert api_key_response.is_active is True
        assert api_key_response.scopes == ["repo:read", "claims:read"]
    
    async def test_verify_api_key_success(self, async_session, test_user):
        """Test successful API key verification."""
        auth_service = AuthenticationService(async_session)
        
        # Create API key
        key_data = APIKeyCreate(
            name="Test API Key",
            description="API key for testing",
            scopes=["repo:read"]
        )
        api_key_response = await auth_service.create_api_key(test_user.id, key_data)
        
        # Verify API key
        verified_user = await auth_service.verify_api_key(api_key_response.key)
        
        assert verified_user is not None
        assert verified_user.id == test_user.id
        assert verified_user.email == test_user.email
    
    async def test_verify_api_key_invalid(self, async_session):
        """Test API key verification with invalid key."""
        auth_service = AuthenticationService(async_session)
        
        verified_user = await auth_service.verify_api_key("invalid_key")
        
        assert verified_user is None
    
    async def test_verify_api_key_expired(self, async_session, test_user):
        """Test API key verification with expired key."""
        auth_service = AuthenticationService(async_session)
        
        # Create API key that expires in the past
        past_time = datetime.now(timezone.utc) - timedelta(days=1)
        key_data = APIKeyCreate(
            name="Expired API Key",
            description="Expired API key for testing",
            expires_at=past_time,
            scopes=["repo:read"]
        )
        api_key_response = await auth_service.create_api_key(test_user.id, key_data)
        
        # Try to verify expired key
        verified_user = await auth_service.verify_api_key(api_key_response.key)
        
        assert verified_user is None


@pytest.mark.unit
class TestValidationUtils:
    """Test input validation utilities."""
    
    def test_validate_email_valid(self):
        """Test email validation with valid emails."""
        valid_emails = [
            "test@example.com",
            "user.name@domain.co.uk",
            "user+tag@example.org",
            "123@numbers.com"
        ]
        
        for email in valid_emails:
            assert validate_email(email) is True
    
    def test_validate_email_invalid(self):
        """Test email validation with invalid emails."""
        invalid_emails = [
            "invalid-email",
            "@domain.com",
            "user@",
            "user@domain",
            "user name@domain.com",
            ""
        ]
        
        for email in invalid_emails:
            assert validate_email(email) is False
    
    def test_validate_url_valid(self):
        """Test URL validation with valid URLs."""
        valid_urls = [
            "https://example.com",
            "http://test.org",
            "https://api.github.com/repos/owner/repo",
            "http://localhost:8000/api"
        ]
        
        for url in valid_urls:
            assert validate_url(url) is True
    
    def test_validate_url_invalid(self):
        """Test URL validation with invalid URLs."""
        invalid_urls = [
            "not-a-url",
            "ftp://example.com",  # Only http/https allowed
            "example.com",  # Missing protocol
            "",
            "javascript:alert('xss')"
        ]
        
        for url in invalid_urls:
            assert validate_url(url) is False