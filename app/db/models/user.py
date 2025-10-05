"""
User and authentication models for Cookie Licking Detector.
"""

import enum
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.database import Base


class UserRole(enum.Enum):
    """User roles for role-based access control."""
    ADMIN = "admin"
    MAINTAINER = "maintainer"
    USER = "user"


class User(Base):
    """User model for authentication and authorization."""
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Role-based access control
    roles: Mapped[List[str]] = mapped_column(
        ARRAY(String), 
        nullable=False, 
        default=[UserRole.USER.value]  # Store string values, not enum objects
    )
    
    # Account status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), 
        nullable=True
    )
    
    # Profile information
    github_username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # User preferences
    preferences: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Relationships - using lazy loading to avoid circular imports
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan", lazy="select")
    repositories = relationship("Repository", back_populates="owner", lazy="select")
    claims = relationship("Claim", back_populates="user", lazy="select")
    
    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', roles={self.roles})>"
    
    def has_role(self, role: UserRole) -> bool:
        """Check if user has a specific role."""
        return role.value in self.roles
    
    def has_any_role(self, roles: List[UserRole]) -> bool:
        """Check if user has any of the specified roles."""
        return any(role.value in self.roles for role in roles)
    
    def is_admin(self) -> bool:
        """Check if user is an admin."""
        return UserRole.ADMIN.value in self.roles
    
    def is_maintainer(self) -> bool:
        """Check if user is a maintainer or admin."""
        return any(role in self.roles for role in [UserRole.ADMIN.value, UserRole.MAINTAINER.value])


class APIKey(Base):
    """API Key model for programmatic access."""
    __tablename__ = "api_keys"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # API key details
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    key_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    
    # Permissions and scopes
    scopes: Mapped[List[str]] = mapped_column(
        ARRAY(String),
        nullable=False,
        default=[]
    )
    
    # Status and expiration
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    # Usage tracking
    usage_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_used_ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)  # IPv6 support
    
    # Relationships
    user = relationship("User", back_populates="api_keys")
    
    def __repr__(self):
        return f"<APIKey(id={self.id}, name='{self.name}', user_id={self.user_id})>"
    
    def is_expired(self) -> bool:
        """Check if the API key is expired."""
        if not self.expires_at:
            return False
        return datetime.now(timezone.utc) > self.expires_at
    
    def can_access_scope(self, required_scope: str) -> bool:
        """Check if the API key has access to a specific scope."""
        if not self.scopes:
            return False
        
        # Check for exact match or wildcard
        return required_scope in self.scopes or "*" in self.scopes


class UserSession(Base):
    """User session model for tracking active sessions."""
    __tablename__ = "user_sessions"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Session details
    session_token: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    refresh_token: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Device and location info
    device_info: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Session status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    
    # Relationships
    user = relationship("User")
    
    def __repr__(self):
        return f"<UserSession(id={self.id}, user_id={self.user_id}, is_active={self.is_active})>"
    
    def is_expired(self) -> bool:
        """Check if the session is expired."""
        return datetime.now(timezone.utc) > self.expires_at


class LoginAttempt(Base):
    """Login attempt tracking for security monitoring."""
    __tablename__ = "login_attempts"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Attempt details
    email: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    ip_address: Mapped[str] = mapped_column(String(45), index=True, nullable=False)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Result
    successful: Mapped[bool] = mapped_column(Boolean, nullable=False)
    failure_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Timestamp
    attempted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )
    
    def __repr__(self):
        return f"<LoginAttempt(email='{self.email}', successful={self.successful}, attempted_at={self.attempted_at})>"


class PasswordReset(Base):
    """Password reset token tracking."""
    __tablename__ = "password_resets"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Reset details
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Request details
    ip_address: Mapped[str] = mapped_column(String(45), nullable=False)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    # Relationships
    user = relationship("User")
    
    def __repr__(self):
        return f"<PasswordReset(id={self.id}, user_id={self.user_id}, used={self.used})>"
    
    def is_expired(self) -> bool:
        """Check if the reset token is expired."""
        return datetime.now(timezone.utc) > self.expires_at


# Scopes for API key permissions
class APIScope:
    """Available API scopes for access control."""
    
    # Repository operations
    REPO_READ = "repo:read"
    REPO_WRITE = "repo:write"
    REPO_ADMIN = "repo:admin"
    
    # Claims operations
    CLAIMS_READ = "claims:read"
    CLAIMS_WRITE = "claims:write"
    CLAIMS_ADMIN = "claims:admin"
    
    # User operations
    USER_READ = "user:read"
    USER_WRITE = "user:write"
    USER_ADMIN = "user:admin"
    
    # Analytics
    ANALYTICS_READ = "analytics:read"
    
    # System administration
    SYSTEM_ADMIN = "system:admin"
    
    # Wildcard (full access)
    ALL = "*"
    
    @classmethod
    def get_all_scopes(cls) -> List[str]:
        """Get all available scopes."""
        return [
            cls.REPO_READ, cls.REPO_WRITE, cls.REPO_ADMIN,
            cls.CLAIMS_READ, cls.CLAIMS_WRITE, cls.CLAIMS_ADMIN,
            cls.USER_READ, cls.USER_WRITE, cls.USER_ADMIN,
            cls.ANALYTICS_READ,
            cls.SYSTEM_ADMIN,
            cls.ALL
        ]
    
    @classmethod
    def get_scope_description(cls, scope: str) -> str:
        """Get human-readable description of a scope."""
        descriptions = {
            cls.REPO_READ: "Read repository information",
            cls.REPO_WRITE: "Create and update repositories",
            cls.REPO_ADMIN: "Full repository administration",
            cls.CLAIMS_READ: "Read claim information",
            cls.CLAIMS_WRITE: "Create and update claims",
            cls.CLAIMS_ADMIN: "Full claim administration",
            cls.USER_READ: "Read user information",
            cls.USER_WRITE: "Update user information",
            cls.USER_ADMIN: "Full user administration",
            cls.ANALYTICS_READ: "Read analytics and reports",
            cls.SYSTEM_ADMIN: "Full system administration",
            cls.ALL: "Full access to all resources"
        }
        return descriptions.get(scope, "Unknown scope")