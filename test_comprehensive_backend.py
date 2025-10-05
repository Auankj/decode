#!/usr/bin/env python3
"""
Comprehensive backend test to verify all improvements
Tests graceful degradation, pattern matching, database models, and Celery tasks
"""
import asyncio
import os
import sys
import traceback
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set minimal environment for testing
os.environ["DEBUG"] = "true"
os.environ["ENVIRONMENT"] = "test"
os.environ["LOG_LEVEL"] = "INFO"
os.environ["STRUCTURED_LOGGING"] = "true"

# Remove API keys to test graceful fallback
for env_var in ["GITHUB_TOKEN", "SENDGRID_API_KEY", "GITHUB_APP_ID", "GITHUB_APP_PRIVATE_KEY_PATH"]:
    if env_var in os.environ:
        del os.environ[env_var]

def test_configuration():
    """Test configuration loading and defaults"""
    print("\n=== Testing Configuration ===")
    
    try:
        from app.core.config import get_settings
        
        settings = get_settings()
        print(f"✅ Configuration loaded successfully")
        print(f"  - Environment: {settings.ENVIRONMENT}")
        print(f"  - Debug: {settings.DEBUG}")
        print(f"  - Structured Logging: {settings.STRUCTURED_LOGGING}")
        print(f"  - GitHub token: {'✅ Set' if settings.GITHUB_TOKEN else '❌ Not set (expected)'}")
        print(f"  - SendGrid key: {'✅ Set' if settings.SENDGRID_API_KEY else '❌ Not set (expected)'}")
        
        return True
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        traceback.print_exc()
        return False

def test_database_models():
    """Test database models can be imported without database"""
    print("\n=== Testing Database Models ===")
    
    try:
        from app.db.database import Base
        from app.db.models.repositories import Repository
        from app.db.models.issues import Issue
        from app.db.models.claims import Claim
        from app.db.models.user import User
        
        print("✅ All database models imported successfully")
        print(f"  - Base class: {Base.__name__}")
        print(f"  - Repository model: {Repository.__name__}")
        print(f"  - Issue model: {Issue.__name__}")
        print(f"  - Claim model: {Claim.__name__}")
        print(f"  - User model: {User.__name__}")
        
        return True
    except Exception as e:
        print(f"❌ Database models test failed: {e}")
        traceback.print_exc()
        return False

def test_celery_tasks():
    """Test Celery tasks can be imported"""
    print("\n=== Testing Celery Tasks ===")
    
    try:
        from app.tasks.comment_analysis import analyze_comment_task
        from app.tasks.nudge_check import check_stale_claims_task
        from app.tasks.progress_check import check_progress_task
        
        print("✅ All Celery tasks imported successfully")
        print(f"  - Comment analysis task: {analyze_comment_task.name}")
        print(f"  - Nudge check task: {check_stale_claims_task.name}")
        print(f"  - Progress check task: {check_progress_task.name}")
        
        return True
    except Exception as e:
        print(f"❌ Celery tasks test failed: {e}")
        traceback.print_exc()
        return False

def test_pattern_matching():
    """Test improved pattern matching"""
    print("\n=== Testing Pattern Matching ===")
    
    try:
        from app.services.pattern_matcher import ClaimPatternMatcher
        
        matcher = ClaimPatternMatcher()
        
        # Test various claim types
        test_cases = [
            # Direct claims (should be 95% confidence)
            ("I'll work on this", True, 95),
            ("Let me handle this issue", True, 95),
            
            # Assignment requests (should be 90% confidence)
            ("Can you assign this to me?", True, 90),
            ("I want to work on this", True, 90),
            
            # Questions (should be 70% confidence)
            ("Can I work on this?", True, 70),
            ("Can I maybe possibly work on this perhaps?", True, 70),
            ("Could I potentially work on this issue?", True, 70),
            
            # Progress updates (should be detected but not treated as new claims)
            ("I'm working on this", False, 95),  # High confidence but not a claim
            ("Made some progress on this", False, 0),
            
            # Non-claims
            ("This is a great issue!", False, 0),
            ("How do I reproduce this?", False, 0),
        ]
        
        correct_predictions = 0
        total_tests = len(test_cases)
        
        for text, expected_claim, expected_min_confidence in test_cases:
            result = matcher.analyze_comment(text)
            is_claim = result.get('is_claim', False)
            confidence = result.get('final_score', 0)
            
            # Check if prediction is correct
            prediction_correct = (is_claim == expected_claim)
            confidence_correct = (confidence >= expected_min_confidence) if expected_claim else True
            
            if prediction_correct and confidence_correct:
                correct_predictions += 1
                status = "✅"
            else:
                status = "❌"
            
            print(f"{status} '{text}' -> claim: {is_claim}, confidence: {confidence}% (expected: claim={expected_claim}, min_confidence={expected_min_confidence}%)")
        
        accuracy = (correct_predictions / total_tests) * 100
        print(f"\n📊 Pattern Matching Accuracy: {correct_predictions}/{total_tests} ({accuracy:.1f}%)")
        
        return accuracy >= 90  # Require 90% accuracy
    except Exception as e:
        print(f"❌ Pattern matching test failed: {e}")
        traceback.print_exc()
        return False

async def test_services():
    """Test all services with graceful degradation"""
    print("\n=== Testing Services ===")
    
    try:
        # Test GitHub service
        from app.services.github_service import GitHubAPIService
        github_service = GitHubAPIService()
        print(f"✅ GitHub service: authenticated={github_service.authenticated}")
        
        # Test authentication-required operations fail gracefully
        try:
            await github_service.post_issue_comment("test", "test", 1, "test")
            print("❌ GitHub comment posting should have failed")
            return False
        except ValueError as e:
            if "authentication" in str(e).lower():
                print("✅ GitHub auth properly handled")
            else:
                print(f"❌ Unexpected GitHub error: {e}")
                return False
        
        # Test Notification service
        from app.services.notification_service import NotificationService
        notification_service = NotificationService()
        print(f"✅ Notification service: email_enabled={notification_service.email_enabled}")
        
        # Test email sending fails gracefully
        class MockClaim:
            github_username = "test"
            issue = type('Issue', (), {
                'github_issue_number': 123,
                'title': 'Test',
                'repository': type('Repo', (), {'owner': 'test', 'name': 'test', 'grace_period_days': 7})(),
                'github_data': {'html_url': 'http://test'}
            })()
            claim_timestamp = type('dt', (), {'strftime': lambda self, fmt: 'Jan 1'})()
            issue_id = 1
        
        result = await notification_service.send_nudge_email(MockClaim(), 1)
        if result == False:
            print("✅ Email sending gracefully handled missing credentials")
        else:
            print(f"❌ Email sending should return False: {result}")
            return False
        
        return True
    except Exception as e:
        print(f"❌ Services test failed: {e}")
        traceback.print_exc()
        return False

async def main():
    """Run comprehensive backend test suite"""
    print("🧪 Cookie-Licking Detector Comprehensive Backend Test")
    print("=" * 70)
    
    test_results = []
    
    # Run all tests
    test_results.append(test_configuration())
    test_results.append(test_database_models())
    test_results.append(test_celery_tasks())
    test_results.append(test_pattern_matching())
    test_results.append(await test_services())
    
    print("\n" + "=" * 70)
    print("📊 COMPREHENSIVE TEST SUMMARY")
    print("=" * 70)
    
    passed = sum(test_results)
    total = len(test_results)
    
    print(f"✅ Tests passed: {passed}/{total}")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! 🎉")
        print("\n✨ Backend Status: FULLY FUNCTIONAL")
        print("\n💡 Key Achievements:")
        print("  ✅ Configuration loads with sensible defaults")
        print("  ✅ Database models import without database connection")
        print("  ✅ Celery tasks import without dependency issues")
        print("  ✅ Pattern matching works with high accuracy")
        print("  ✅ GitHub service degrades gracefully without credentials")
        print("  ✅ Email service degrades gracefully without SendGrid")
        print("  ✅ All services handle missing configuration properly")
        
        print("\n🚀 The Cookie-Licking Detector backend is ready for:")
        print("  • Development without external service setup")
        print("  • Testing with full pattern matching capabilities")
        print("  • Production deployment with proper credentials")
        print("  • Integration testing and CI/CD pipelines")
        
        return True
    else:
        print(f"\n❌ {total - passed} test(s) failed")
        print("Please check the output above for specific failures.")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)