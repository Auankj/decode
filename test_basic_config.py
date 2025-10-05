#!/usr/bin/env python3
"""
Test script to verify basic configuration and imports work
"""
import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def test_basic_imports():
    """Test that all core modules can be imported"""
    print("🧪 Testing Basic Module Imports...")
    print("=" * 50)
    
    all_passed = True
    
    # Test core service imports
    test_modules = [
        ("Pattern Matcher", "app.services.pattern_matcher"),
        ("GitHub Service", "app.services.github_service"), 
        ("Notification Service", "app.services.notification_service"),
        ("Ecosyste Client", "app.services.ecosyste_client"),
        ("Config", "app.core.config"),
        ("Logging", "app.core.logging"),
        ("Security", "app.core.security"),
        ("Monitoring", "app.core.monitoring"),
        ("Celery App", "app.core.celery_app"),
        ("Database", "app.db.database"),
        ("Distributed Lock", "app.utils.distributed_lock"),
    ]
    
    for name, module_path in test_modules:
        try:
            __import__(module_path)
            print(f"✅ {name} - Import successful")
        except Exception as e:
            print(f"❌ {name} - Import failed: {e}")
            all_passed = False
    
    print("=" * 50)
    
    # Test model imports
    print("\n🧪 Testing Database Model Imports...")
    print("=" * 50)
    
    model_modules = [
        ("Claims Model", "app.db.models.claims"),
        ("Issues Model", "app.db.models.issues"), 
        ("Repositories Model", "app.db.models.repositories"),
        ("Activity Log Model", "app.db.models.activity_log"),
        ("Progress Tracking Model", "app.db.models.progress_tracking"),
        ("Queue Jobs Model", "app.db.models.queue_jobs"),
        ("User Model", "app.db.models.user"),
    ]
    
    for name, module_path in model_modules:
        try:
            __import__(module_path)
            print(f"✅ {name} - Import successful")
        except Exception as e:
            print(f"❌ {name} - Import failed: {e}")
            all_passed = False
    
    print("=" * 50)
    
    # Test task imports
    print("\n🧪 Testing Task Module Imports...")
    print("=" * 50)
    
    task_modules = [
        ("Comment Analysis Task", "app.tasks.comment_analysis"),
        ("Nudge Check Task", "app.tasks.nudge_check"),
        ("Progress Check Task", "app.tasks.progress_check"),
    ]
    
    for name, module_path in task_modules:
        try:
            __import__(module_path)
            print(f"✅ {name} - Import successful")
        except Exception as e:
            print(f"❌ {name} - Import failed: {e}")
            all_passed = False
    
    print("=" * 50)
    
    if all_passed:
        print("🎉 All module imports PASSED!")
        return True
    else:
        print("💥 Some module imports FAILED!")
        return False

def test_environment_setup():
    """Test basic environment setup"""
    print("\n🧪 Testing Environment Setup...")
    print("=" * 50)
    
    # Check if basic environment variables exist or have defaults
    env_vars = [
        "DATABASE_URL",
        "REDIS_URL", 
        "GITHUB_TOKEN",
        "SENDGRID_API_KEY",
        "FROM_EMAIL",
        "SECRET_KEY"
    ]
    
    for var in env_vars:
        value = os.getenv(var)
        if value:
            print(f"✅ {var} - Set (length: {len(value)})")
        else:
            print(f"⚠️  {var} - Not set (will use defaults)")
    
    print("=" * 50)
    return True

if __name__ == "__main__":
    import_success = test_basic_imports()
    env_success = test_environment_setup()
    
    sys.exit(0 if import_success and env_success else 1)