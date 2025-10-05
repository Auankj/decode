#!/usr/bin/env python3
"""
Test script to start the Cookie Licking Detector API server with minimal dependencies
"""
import os
import sys
from contextlib import asynccontextmanager
from unittest.mock import patch, MagicMock, AsyncMock

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set environment
os.environ.setdefault('ENVIRONMENT', 'development')
os.environ.setdefault('DATABASE_URL', 'sqlite+aiosqlite:///./test.db')  # Use SQLite for testing

import uvicorn
from fastapi import FastAPI

# Create a simplified lifespan manager that doesn't require database
@asynccontextmanager
async def minimal_lifespan(app: FastAPI):
    """Minimal lifespan without database operations"""
    print("Starting Cookie Licking Detector API (minimal mode)...")
    yield
    print("Shutting down Cookie Licking Detector API")

# Mock the database components before importing main app
with patch('app.db.database.get_async_session'), \
     patch('app.db.database.create_tables'), \
     patch('app.db.database.close_db'), \
     patch('sqlalchemy.ext.asyncio.create_async_engine'), \
     patch('sqlalchemy.pool.QueuePool'), \
     patch('app.db.database.async_sessionmaker'), \
     patch('app.core.monitoring.health_checker'), \
     patch('app.core.config.get_settings') as mock_settings:
    
    # Create mock settings that don't require database
    from app.core.config import Settings
    mock_settings_instance = Settings()
    mock_settings_instance.DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite+aiosqlite:///./test.db')
    mock_settings_instance.ENVIRONMENT = "development"
    mock_settings_instance.DEBUG = True
    mock_settings_instance.DB_ECHO = False
    mock_settings.return_value = mock_settings_instance
    
    # Import the main app after mocking
    from app.main import app, logger
    
    # Override the lifespan to avoid database operations
    app.router.lifespan_context = minimal_lifespan(app) if hasattr(app.router, 'lifespan_context') else minimal_lifespan
    
    print("Starting Cookie Licking Detector server on http://localhost:8001 (port changed to avoid conflicts)...")
    print("API endpoints will be available, but database operations will be mocked")
    print("Press Ctrl+C to stop the server")
    
    # Run the server on port 8001 to avoid conflicts
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")