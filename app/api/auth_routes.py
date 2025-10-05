"""
Authentication API routes for Cookie Licking Detector.
Handles user registration, login, JWT tokens, and API key management.
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    AuthenticationService, SecurityUtils, jwt_manager,
    UserCreate, UserLogin, APIKeyCreate, Token,
    get_current_user, get_current_active_user, require_admin,
    get_client_ip, add_security_headers
)
from app.core.logging import get_logger
from app.core.monitoring import track_api_call
from app.db.database import get_async_session
from app.db.models.user import User, UserRole

router = APIRouter(prefix="/auth", tags=["authentication"])
logger = get_logger(__name__)
security = HTTPBearer(auto_error=False)


@router.post("/register", status_code=201)
async def register_user(
    user_data: UserCreate,
    request: Request,
    db: AsyncSession = Depends(get_async_session)
):
    """Register a new user."""
    try:
        auth_service = AuthenticationService(db)
        
        # Create user
        user = await auth_service.create_user(user_data)
        
        # Track API call
        track_api_call("auth", "register", 201)
        
        logger.info(f"User registered successfully: {user.email}")
        
        return {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "roles": user.roles,  # Already strings, no need for .value
            "is_active": user.is_active,
            "created_at": user.created_at
        }
        
    except HTTPException:
        track_api_call("auth", "register", 400)
        raise
    except Exception as e:
        track_api_call("auth", "register", 500)
        logger.error(f"Registration failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/login", response_model=Token)
async def login(
    user_data: UserLogin,
    request: Request,
    db: AsyncSession = Depends(get_async_session)
):
    """Login user and return JWT tokens."""
    try:
        auth_service = AuthenticationService(db)
        
        # Authenticate user
        user = await auth_service.authenticate_user(
            user_data.email, 
            user_data.password
        )
        
        if not user:
            track_api_call("auth", "login", 401)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Create token pair
        tokens = jwt_manager.create_token_pair(user)
        
        track_api_call("auth", "login", 200)
        logger.info(f"User logged in: {user.email}")
        
        return tokens
        
    except HTTPException:
        raise
    except Exception as e:
        track_api_call("auth", "login", 500)
        logger.error(f"Login failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_data: dict,
    request: Request,
    db: AsyncSession = Depends(get_async_session)
):
    """Refresh access token using refresh token."""
    try:
        refresh_token = refresh_data.get("refresh_token")
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Refresh token required"
            )
        
        # Verify refresh token
        token_data = jwt_manager.verify_token(refresh_token)
        
        if token_data.token_type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token type"
            )
        
        # Get user
        auth_service = AuthenticationService(db)
        user = await auth_service.get_user_by_id(token_data.user_id)
        
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        # Create new token pair
        tokens = jwt_manager.create_token_pair(user)
        
        track_api_call("auth", "refresh", 200)
        return tokens
        
    except HTTPException:
        track_api_call("auth", "refresh", 401)
        raise
    except Exception as e:
        track_api_call("auth", "refresh", 500)
        logger.error(f"Token refresh failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )


@router.get("/me")
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """Get current user information."""
    track_api_call("auth", "me", 200)
    
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "roles": current_user.roles,  # Already strings, no need for .value
        "is_active": current_user.is_active,
        "is_verified": current_user.is_verified,
        "github_username": current_user.github_username,
        "created_at": current_user.created_at,
        "last_login_at": current_user.last_login_at
    }


@router.post("/logout")
async def logout(
    request: Request,
    current_user: User = Depends(get_current_active_user)
):
    """Logout user (invalidate token)."""
    # In a production system, you would add the token to a blacklist
    # For now, we just log the logout
    
    track_api_call("auth", "logout", 200)
    logger.info(f"User logged out: {current_user.email}")
    
    return {"message": "Successfully logged out"}


@router.post("/api-keys", status_code=201)
async def create_api_key(
    key_data: APIKeyCreate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Create a new API key for the current user."""
    try:
        auth_service = AuthenticationService(db)
        
        api_key_response = await auth_service.create_api_key(
            current_user.id, 
            key_data
        )
        
        track_api_call("auth", "create_api_key", 201)
        logger.info(f"API key created for user {current_user.id}: {key_data.name}")
        
        return api_key_response
        
    except Exception as e:
        track_api_call("auth", "create_api_key", 500)
        logger.error(f"API key creation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API key creation failed"
        )


@router.get("/api-keys")
async def list_api_keys(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_session)
):
    """List API keys for the current user."""
    try:
        from sqlalchemy import select
        from app.db.models.user import APIKey
        
        stmt = select(APIKey).where(APIKey.user_id == current_user.id)
        result = await db.execute(stmt)
        api_keys = result.scalars().all()
        
        track_api_call("auth", "list_api_keys", 200)
        
        return [
            {
                "id": key.id,
                "name": key.name,
                "description": key.description,
                "scopes": key.scopes,
                "is_active": key.is_active,
                "created_at": key.created_at,
                "last_used_at": key.last_used_at,
                "expires_at": key.expires_at
            }
            for key in api_keys
        ]
        
    except Exception as e:
        track_api_call("auth", "list_api_keys", 500)
        logger.error(f"API key listing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list API keys"
        )


@router.delete("/api-keys/{key_id}")
async def delete_api_key(
    key_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Delete an API key."""
    try:
        from sqlalchemy import select, delete
        from app.db.models.user import APIKey
        
        # Check if key belongs to current user
        stmt = select(APIKey).where(
            APIKey.id == key_id,
            APIKey.user_id == current_user.id
        )
        result = await db.execute(stmt)
        api_key = result.scalar_one_or_none()
        
        if not api_key:
            track_api_call("auth", "delete_api_key", 404)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found"
            )
        
        # Delete the key
        stmt = delete(APIKey).where(APIKey.id == key_id)
        await db.execute(stmt)
        await db.commit()
        
        track_api_call("auth", "delete_api_key", 200)
        logger.info(f"API key deleted: {key_id}")
        
        return {"message": "API key deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        track_api_call("auth", "delete_api_key", 500)
        logger.error(f"API key deletion failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete API key"
        )


@router.post("/change-password")
async def change_password(
    password_data: dict,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Change user password."""
    try:
        current_password = password_data.get("current_password")
        new_password = password_data.get("new_password")
        confirm_password = password_data.get("confirm_password")
        
        if not all([current_password, new_password, confirm_password]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="All password fields are required"
            )
        
        # Verify current password
        if not SecurityUtils.verify_password(current_password, current_user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        # Check new password confirmation
        if new_password != confirm_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Passwords do not match"
            )
        
        # Validate new password strength
        password_validation = SecurityUtils.validate_password_strength(new_password)
        if not password_validation["is_valid"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Password does not meet requirements",
                    "errors": password_validation["errors"]
                }
            )
        
        # Update password
        current_user.password_hash = SecurityUtils.hash_password(new_password)
        await db.commit()
        
        track_api_call("auth", "change_password", 200)
        logger.info(f"Password changed for user: {current_user.email}")
        
        return {"message": "Password changed successfully"}
        
    except HTTPException:
        track_api_call("auth", "change_password", 400)
        raise
    except Exception as e:
        track_api_call("auth", "change_password", 500)
        logger.error(f"Password change failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password change failed"
        )


@router.post("/request-password-reset")
async def request_password_reset(
    reset_data: dict,
    request: Request
):
    """Request password reset (always returns success for security)."""
    email = reset_data.get("email")
    
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is required"
        )
    
    # Always return success to prevent email enumeration
    # In a real implementation, you would send a reset email if the user exists
    
    track_api_call("auth", "request_password_reset", 200)
    logger.info(f"Password reset requested for: {email}")
    
    return {"message": "If the email exists, a reset link has been sent"}


# Admin endpoints
@router.get("/admin/users")
async def list_all_users(
    page: int = 1,
    per_page: int = 20,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_async_session)
):
    """List all users (admin only)."""
    try:
        from sqlalchemy import select, func
        
        # Get total count
        count_stmt = select(func.count(User.id))
        count_result = await db.execute(count_stmt)
        total = count_result.scalar()
        
        # Get paginated users
        offset = (page - 1) * per_page
        stmt = select(User).offset(offset).limit(per_page)
        result = await db.execute(stmt)
        users = result.scalars().all()
        
        track_api_call("auth", "admin_list_users", 200)
        
        return {
            "users": [
                {
                    "id": user.id,
                    "email": user.email,
                    "full_name": user.full_name,
                    "roles": [role.value for role in user.roles],
                    "is_active": user.is_active,
                    "created_at": user.created_at,
                    "last_login_at": user.last_login_at
                }
                for user in users
            ],
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "pages": (total + per_page - 1) // per_page
            }
        }
        
    except Exception as e:
        track_api_call("auth", "admin_list_users", 500)
        logger.error(f"Admin user listing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list users"
        )