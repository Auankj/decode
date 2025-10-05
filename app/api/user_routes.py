"""
User Management Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from pydantic import BaseModel, EmailStr
from datetime import datetime

from app.db.database import get_async_session
from app.db.models import User
from app.core.security import get_current_user
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()

# Pydantic models
class UserProfile(BaseModel):
    id: int
    email: EmailStr
    github_username: Optional[str]
    full_name: Optional[str]
    bio: Optional[str]
    website: Optional[str]
    location: Optional[str]
    roles: list[str]
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime]
    
    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    github_username: Optional[str] = None
    full_name: Optional[str] = None
    bio: Optional[str] = None
    website: Optional[str] = None
    location: Optional[str] = None

@router.get("/users/me", response_model=UserProfile)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    """
    Get current authenticated user's profile
    """
    return UserProfile(
        id=current_user.id,
        email=current_user.email,
        github_username=current_user.github_username,
        full_name=current_user.full_name,
        bio=current_user.bio,
        website=current_user.website,
        location=current_user.location,
        roles=current_user.roles,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
        last_login_at=current_user.last_login_at
    )

@router.put("/users/me", response_model=UserProfile)
async def update_current_user_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Update current authenticated user's profile
    """
    try:
        # Update user fields if provided
        if user_update.github_username is not None:
            current_user.github_username = user_update.github_username
        if user_update.full_name is not None:
            current_user.full_name = user_update.full_name
        if user_update.bio is not None:
            current_user.bio = user_update.bio
        if user_update.website is not None:
            current_user.website = user_update.website
        if user_update.location is not None:
            current_user.location = user_update.location
            
        current_user.updated_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(current_user)
        
        logger.info(f"User profile updated: {current_user.email}")
        
        return UserProfile(
            id=current_user.id,
            email=current_user.email,
            github_username=current_user.github_username,
            full_name=current_user.full_name,
            bio=current_user.bio,
            website=current_user.website,
            location=current_user.location,
            roles=current_user.roles,
            is_active=current_user.is_active,
            is_verified=current_user.is_verified,
            created_at=current_user.created_at,
            updated_at=current_user.updated_at,
            last_login_at=current_user.last_login_at
        )
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating user profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating user profile"
        )

@router.get("/users/me/preferences")
async def get_user_preferences(
    current_user: User = Depends(get_current_user)
):
    """
    Get user's notification and application preferences
    """
    return {
        "user_id": current_user.id,
        "preferences": current_user.preferences or {},
        "notification_settings": {
            "email_notifications": True,
            "webhook_notifications": True,
            "claim_updates": True,
            "progress_updates": True
        }
    }

@router.put("/users/me/preferences")
async def update_user_preferences(
    preferences: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Update user's preferences
    """
    try:
        current_user.preferences = preferences
        current_user.updated_at = datetime.utcnow()
        
        await db.commit()
        
        logger.info(f"User preferences updated: {current_user.email}")
        
        return {
            "message": "Preferences updated successfully",
            "preferences": preferences
        }
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating user preferences: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating preferences"
        )