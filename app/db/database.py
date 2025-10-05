"""
Database configuration and session management for Cookie Licking Detector.
Production-ready async database setup with connection pooling.
"""

import os
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.pool import QueuePool

from app.core.config import get_settings

# Base class for all models (can be imported without engine)
Base = declarative_base()

# Global variables for lazy initialization
_engine = None
_async_session_factory = None

def get_engine():
    """Get or create database engine with lazy initialization"""
    global _engine
    if _engine is None:
        settings = get_settings()
        
        # Convert database URL for async if needed
        db_url = settings.DATABASE_URL
        if db_url.startswith("postgresql://"):
            db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")
        
        try:
            # For async engines, don't use QueuePool - it's not compatible
            _engine = create_async_engine(
                db_url,
                echo=settings.DB_ECHO,
                pool_size=settings.DATABASE_POOL_SIZE,
                max_overflow=settings.DATABASE_MAX_OVERFLOW,
                pool_pre_ping=True,
                pool_recycle=settings.DATABASE_POOL_RECYCLE,
                connect_args={
                    "server_settings": {
                        "application_name": "cookie-licking-detector",
                    }
                } if "postgresql" in db_url else {}
            )
        except Exception as e:
            print(f"Warning: Could not create database engine: {e}")
            _engine = None
    return _engine

def get_async_session_factory():
    """Get or create async session factory with lazy initialization"""
    global _async_session_factory
    if _async_session_factory is None:
        engine = get_engine()
        if engine:
            _async_session_factory = async_sessionmaker(
                engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
    return _async_session_factory

# Legacy property access for backward compatibility
@property
def engine():
    return get_engine()

@property
def async_session_factory():
    return get_async_session_factory()


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting async database session.
    """
    session_factory = get_async_session_factory()
    if not session_factory:
        raise RuntimeError("Database not properly configured")
        
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_tables():
    """Create all database tables."""
    # Import all models to ensure they're registered with Base.metadata
    from . import models
    
    engine = get_engine()
    if not engine:
        raise RuntimeError("Database engine not available")
        
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_tables():
    """Drop all database tables."""
    engine = get_engine()
    if not engine:
        raise RuntimeError("Database engine not available")
        
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def close_db():
    """Close database connections with graceful error handling."""
    global _engine, _async_session_factory
    
    try:
        if _engine is not None:
            await _engine.dispose()
    except Exception as e:
        # Log but don't raise - shutdown should continue
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Error disposing database engine during shutdown: {e}")
    finally:
        # Reset global variables
        _engine = None
        _async_session_factory = None


# Legacy sync session for backward compatibility (if needed)
def get_db():
    """Legacy sync database session for existing sync routes."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker, Session
    
    # Create sync engine for legacy compatibility
    sync_engine = create_engine(
        settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://"),
        poolclass=QueuePool,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        pool_recycle=300
    )
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)
    
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
