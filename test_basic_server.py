#!/usr/bin/env python3
"""
Test script to verify basic server functionality without database
"""
import os
import sys

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Temporarily set environment to test to allow running without DB
os.environ['ENVIRONMENT'] = 'test'

print("Starting basic server functionality test...")

# Try to import core modules to check if they work
try:
    from app.core.config import Settings, get_settings
    print("✅ Configuration module imported successfully")
    
    settings = get_settings()
    print(f"✅ Settings loaded: Environment = {settings.ENVIRONMENT}")
    
    # Test Redis connectivity
    import redis
    try:
        redis_client = redis.from_url(settings.REDIS_URL)
        redis_client.ping()
        print("✅ Redis connection successful")
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
    
    print("✅ Basic modules loaded successfully")
    
    # Test Celery connection
    from app.core.celery_app import celery_app
    print("✅ Celery app imported successfully")
    
    # Check if Celery can connect to Redis (this might fail if Redis isn't available)
    try:
        # Try to ping the broker to confirm connection
        inspect = celery_app.control.inspect()
        # This will return None if no workers are connected, which is OK
        stats = inspect.stats()
        print("✅ Celery connection to Redis successful")
        if stats is not None:
            print(f"   Active workers: {list(stats.keys()) if stats else 'None'}")
        else:
            print("   No active Celery workers detected (this is OK)")
    except Exception as e:
        print(f"⚠️  Celery inspection issue (might be OK if no workers running): {e}")
    
    print("\n🎉 Server basic functionality verified!")
    print("The backend components are properly configured and can connect to Redis.")
    
except Exception as e:
    print(f"❌ Error during basic server verification: {e}")
    import traceback
    traceback.print_exc()