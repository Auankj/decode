"""
Comprehensive authentication and security system for Cookie Licking Detector.
Includes JWT authentication, API key management, rate limiting, and security utilities.
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4

import bcrypt
from fastapi import HTTPException, Request, Security, status, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, APIKeyHeader
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.models.user import User, APIKey, UserRole
from app.db.database import get_async_session

settings = get_settings()
logger = get_logger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security schemes
bearer_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


class TokenData(BaseModel):
    """Token payload data."""
    user_id: Optional[int] = None
    email: Optional[str] = None
    roles: List[str] = []
    token_type: str = "access"


class Token(BaseModel):
    """Token response model."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserCreate(BaseModel):
    """User creation model."""
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    roles: List[UserRole] = [UserRole.USER]


class UserLogin(BaseModel):
    """User login model."""
    email: EmailStr
    password: str


class APIKeyCreate(BaseModel):
    """API key creation model."""
    name: str
    description: Optional[str] = None
    expires_at: Optional[datetime] = None
    scopes: List[str] = []


class APIKeyResponse(BaseModel):
    """API key response model."""
    id: int
    name: str
    key: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    is_active: bool
    scopes: List[str]


class SecurityUtils:
    """Security utility functions."""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt."""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    @staticmethod
    def verify_password(password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        try:
            return bcrypt.checkpw(
                password.encode('utf-8'), 
                hashed_password.encode('utf-8')
            )
        except Exception as e:
            logger.error(f"Password verification failed: {e}")
            return False
    
    @staticmethod
    def generate_api_key() -> str:
        """Generate a secure API key."""
        # Generate a secure random key
        key_bytes = secrets.token_bytes(32)
        # Create a readable key with prefix
        key = f"ckd_{key_bytes.hex()}"
        return key
    
    @staticmethod
    def hash_api_key(api_key: str) -> str:
        """Hash an API key for storage."""
        return hashlib.sha256(api_key.encode()).hexdigest()
    
    @staticmethod
    def generate_token_secret() -> str:
        """Generate a secure token for JWT signing."""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def sanitize_input(text: str, max_length: int = 1000) -> str:
        """Sanitize user input."""
        if not text:
            return ""
        
        # Remove dangerous characters and limit length
        sanitized = text.strip()[:max_length]
        
        # Remove potentially dangerous patterns
        dangerous_patterns = ['<script', 'javascript:', 'onload=', 'onerror=']
        for pattern in dangerous_patterns:
            sanitized = sanitized.replace(pattern, '')
        
        return sanitized
    
    @staticmethod
    def validate_password_strength(password: str) -> Dict[str, Any]:
        """Validate password strength."""
        errors = []
        
        if len(password) < 8:
            errors.append("Password must be at least 8 characters long")
        
        if not any(c.isupper() for c in password):
            errors.append("Password must contain at least one uppercase letter")
        
        if not any(c.islower() for c in password):
            errors.append("Password must contain at least one lowercase letter")
        
        if not any(c.isdigit() for c in password):
            errors.append("Password must contain at least one number")
        
        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        if not any(c in special_chars for c in password):
            errors.append("Password must contain at least one special character")
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors
        }


class JWTManager:
    """JWT token management."""
    
    def __init__(self):
        self.secret_key = settings.SECRET_KEY
        self.algorithm = settings.JWT_ALGORITHM
        self.access_token_expire_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES
        self.refresh_token_expire_days = settings.REFRESH_TOKEN_EXPIRE_DAYS
    
    def create_access_token(self, data: Dict[str, Any]) -> str:
        """Create an access token."""
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=self.access_token_expire_minutes
        )
        to_encode.update({
            "exp": expire,
            "type": "access",
            "iat": datetime.now(timezone.utc),
            "jti": str(uuid4())
        })
        
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
    
    def create_refresh_token(self, data: Dict[str, Any]) -> str:
        """Create a refresh token."""
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(
            days=self.refresh_token_expire_days
        )
        to_encode.update({
            "exp": expire,
            "type": "refresh",
            "iat": datetime.now(timezone.utc),
            "jti": str(uuid4())
        })
        
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str) -> TokenData:
        """Verify and decode a JWT token."""
        try:
            payload = jwt.decode(
                token, self.secret_key, algorithms=[self.algorithm]
            )
            
            user_id_str: str = payload.get("sub")
            email: str = payload.get("email")
            roles: List[str] = payload.get("roles", [])
            token_type: str = payload.get("type", "access")
            
            if user_id_str is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token: missing user ID"
                )
            
            try:
                user_id = int(user_id_str)
            except (ValueError, TypeError):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token: invalid user ID"
                )
            
            return TokenData(
                user_id=user_id,
                email=email,
                roles=roles,
                token_type=token_type
            )
        except JWTError as e:
            logger.warning(f"JWT verification failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials"
            )
    
    def create_token_pair(self, user: User) -> Token:
        """Create both access and refresh tokens for a user."""
        token_data = {
            "sub": str(user.id),  # JWT subject must be a string
            "email": user.email,
            "roles": user.roles  # Already strings, no need for .value
        }
        
        access_token = self.create_access_token(token_data)
        refresh_token = self.create_refresh_token(token_data)
        
        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=self.access_token_expire_minutes * 60
        )


# Global JWT manager instance
jwt_manager = JWTManager()


class AuthenticationService:
    """Authentication service for user management."""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
    
    async def create_user(self, user_data: UserCreate) -> User:
        """Create a new user."""
        # Check if user already exists
        stmt = select(User).where(User.email == user_data.email)
        result = await self.db.execute(stmt)
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )
        
        # Validate password strength
        password_validation = SecurityUtils.validate_password_strength(user_data.password)
        if not password_validation["is_valid"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Password does not meet requirements",
                    "errors": password_validation["errors"]
                }
            )
        
        # Create new user
        hashed_password = SecurityUtils.hash_password(user_data.password)
        
        new_user = User(
            email=user_data.email,
            password_hash=hashed_password,
            full_name=user_data.full_name,
            roles=[role.value for role in user_data.roles],  # Convert enums to strings
            is_active=True,
            created_at=datetime.now(timezone.utc)
        )
        
        self.db.add(new_user)
        await self.db.commit()
        await self.db.refresh(new_user)
        
        logger.info(f"New user created: {new_user.email}")
        return new_user
    
    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate a user with email and password."""
        stmt = select(User).where(User.email == email)
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user or not user.is_active:
            return None
        
        if not SecurityUtils.verify_password(password, user.password_hash):
            logger.warning(f"Failed login attempt for user: {email}")
            return None
        
        # Update last login
        user.last_login_at = datetime.now(timezone.utc)
        await self.db.commit()
        
        logger.info(f"User authenticated successfully: {email}")
        return user
    
    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        stmt = select(User).where(User.id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def create_api_key(self, user_id: int, key_data: APIKeyCreate) -> APIKeyResponse:
        """Create a new API key for a user."""
        # Generate API key
        api_key = SecurityUtils.generate_api_key()
        api_key_hash = SecurityUtils.hash_api_key(api_key)
        
        # Create API key record
        new_api_key = APIKey(
            user_id=user_id,
            name=key_data.name,
            description=key_data.description,
            key_hash=api_key_hash,
            scopes=key_data.scopes,
            expires_at=key_data.expires_at,
            is_active=True,
            created_at=datetime.now(timezone.utc)
        )
        
        self.db.add(new_api_key)
        await self.db.commit()
        await self.db.refresh(new_api_key)
        
        logger.info(f"API key created for user {user_id}: {key_data.name}")
        
        return APIKeyResponse(
            id=new_api_key.id,
            name=new_api_key.name,
            key=api_key,  # Only returned once during creation
            created_at=new_api_key.created_at,
            expires_at=new_api_key.expires_at,
            is_active=new_api_key.is_active,
            scopes=new_api_key.scopes
        )
    
    async def verify_api_key(self, api_key: str) -> Optional[User]:
        """Verify an API key and return the associated user."""
        api_key_hash = SecurityUtils.hash_api_key(api_key)
        
        stmt = select(APIKey).where(
            APIKey.key_hash == api_key_hash,
            APIKey.is_active == True
        )
        result = await self.db.execute(stmt)
        api_key_record = result.scalar_one_or_none()
        
        if not api_key_record:
            return None
        
        # Check expiration
        if api_key_record.expires_at and api_key_record.expires_at < datetime.now(timezone.utc):
            logger.warning(f"Expired API key used: {api_key_record.name}")
            return None
        
        # Get associated user
        user = await self.get_user_by_id(api_key_record.user_id)
        
        if user and user.is_active:
            # Update last used timestamp
            api_key_record.last_used_at = datetime.now(timezone.utc)
            await self.db.commit()
            
            logger.info(f"API key authenticated: {api_key_record.name}")
            return user
        
        return None


# Dependency functions for FastAPI
async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
    api_key: Optional[str] = Security(api_key_header),
    db: AsyncSession = Depends(get_async_session)
) -> User:
    """Get current authenticated user from JWT token or API key."""
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    auth_service = AuthenticationService(db)
    
    # Try API key authentication first
    if api_key:
        user = await auth_service.verify_api_key(api_key)
        if user:
            return user
    
    # Try JWT token authentication
    if credentials and credentials.credentials:
        try:
            token_data = jwt_manager.verify_token(credentials.credentials)
            user = await auth_service.get_user_by_id(token_data.user_id)
            if user and user.is_active:
                return user
        except HTTPException:
            pass
    
    raise credentials_exception


async def get_current_active_user(
    current_user: User = Security(get_current_user)
) -> User:
    """Get current active user."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


def require_roles(allowed_roles: List[UserRole]):
    """Dependency to require specific user roles."""
    async def role_checker(current_user: User = Security(get_current_active_user)) -> User:
        allowed_role_values = [role.value for role in allowed_roles]
        if not any(role in current_user.roles for role in allowed_role_values):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
        return current_user
    
    return role_checker


# Role-based dependencies
require_admin = require_roles([UserRole.ADMIN])
require_maintainer = require_roles([UserRole.ADMIN, UserRole.MAINTAINER])
require_user = require_roles([UserRole.ADMIN, UserRole.MAINTAINER, UserRole.USER])


# Rate limiting utilities
class RateLimitExceeded(HTTPException):
    """Rate limit exceeded exception."""
    def __init__(self, detail: str = "Rate limit exceeded"):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail
        )


def get_client_ip(request: Request) -> str:
    """Get client IP address from request."""
    # Check for forwarded headers (behind proxy)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Fallback to client host
    return request.client.host if request.client else "unknown"


# Input validation utilities
def validate_email(email: str) -> bool:
    """Validate email format."""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_url(url: str) -> bool:
    """Validate URL format."""
    import re
    pattern = r'^https?://.+'
    return bool(re.match(pattern, url))


# Function exports for easier access
def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt."""
    return SecurityUtils.hash_password(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return SecurityUtils.verify_password(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create an access token."""
    return jwt_manager.create_access_token(data)

def verify_token(token: str) -> TokenData:
    """Verify and decode a JWT token."""
    return jwt_manager.verify_token(token)

# Security headers middleware
def add_security_headers(response):
    """Add security headers to response."""
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "connect-src 'self';"
    )
    return response
