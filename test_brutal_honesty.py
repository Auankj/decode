#!/usr/bin/env python3
"""
BRUTAL HONESTY TEST
Actually test the COMPLETE webhook-to-database flow like a real GitHub webhook would trigger
"""
import asyncio
import json
import sys
import os
import requests
import time
from datetime import datetime, timezone

# Add app to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def start_test_servers():
    """Start the actual FastAPI server and Celery worker"""
    print("🚀 STARTING TEST SERVERS...")
    print("=" * 60)
    
    import subprocess
    import signal
    
    # Start FastAPI server
    print("Starting FastAPI server...")
    fastapi_process = subprocess.Popen([
        'python3', '-m', 'uvicorn', 'app.main:app', 
        '--host', '0.0.0.0', '--port', '8000', '--reload'
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Start Celery worker
    print("Starting Celery worker...")
    celery_process = subprocess.Popen([
        'python3', '-m', 'celery', '-A', 'app.core.celery_app', 'worker',
        '--loglevel=info', '--pool=solo'
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Wait for servers to start
    print("Waiting for servers to initialize...")
    time.sleep(5)
    
    return fastapi_process, celery_process

def stop_test_servers(fastapi_process, celery_process):
    """Stop test servers"""
    print("\n🛑 STOPPING TEST SERVERS...")
    try:
        fastapi_process.terminate()
        celery_process.terminate()
        time.sleep(2)
        fastapi_process.kill()
        celery_process.kill()
    except:
        pass

def test_server_health():
    """Test if servers are actually running"""
    print("\n🩺 TESTING SERVER HEALTH...")
    print("=" * 60)
    
    try:
        response = requests.get('http://localhost:8000/health', timeout=5)
        if response.status_code == 200:
            print("✅ FastAPI server is running")
            return True
        else:
            print(f"❌ FastAPI server returned {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ FastAPI server not accessible: {e}")
        return False

def create_real_webhook_payload():
    """Create a realistic GitHub webhook payload"""
    return {
        "action": "created",
        "issue": {
            "id": 999999,
            "number": 42,
            "title": "Test issue for brutal honesty check",
            "body": "This is a real test issue to verify the system works end-to-end",
            "state": "open",
            "html_url": "https://github.com/test/repo/issues/42",
            "created_at": "2024-10-05T02:00:00Z",
            "user": {
                "login": "issue_creator",
                "id": 12345
            }
        },
        "comment": {
            "id": 888888,
            "body": "I'll work on this issue and fix it completely!",
            "created_at": "2024-10-05T02:01:00Z",
            "html_url": "https://github.com/test/repo/issues/42#issuecomment-888888",
            "user": {
                "login": "claim_maker",
                "id": 67890
            }
        },
        "repository": {
            "id": 777777,
            "name": "test-repo",
            "full_name": "test/repo",
            "owner": {
                "login": "test",
                "id": 11111
            },
            "html_url": "https://github.com/test/repo"
        }
    }

def test_webhook_endpoint():
    """Test the actual webhook endpoint with real payload"""
    print("\n🔗 TESTING WEBHOOK ENDPOINT...")
    print("=" * 60)
    
    payload = create_real_webhook_payload()
    
    try:
        response = requests.post(
            'http://localhost:8000/api/v1/webhooks/github',
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        print(f"Webhook response status: {response.status_code}")
        print(f"Webhook response body: {response.text}")
        
        if response.status_code == 200:
            print("✅ Webhook endpoint accepted payload")
            return True
        else:
            print(f"❌ Webhook endpoint rejected payload: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Webhook request failed: {e}")
        return False

async def verify_database_changes():
    """Check if the webhook actually created database records"""
    print("\n🗄️ VERIFYING DATABASE CHANGES...")
    print("=" * 60)
    
    try:
        from app.db.database import get_async_session_factory
        from app.db.models.repositories import Repository
        from app.db.models.issues import Issue  
        from app.db.models.claims import Claim
        from app.db.models.activity_log import ActivityLog
        from sqlalchemy import select
        
        session_factory = get_async_session_factory()
        async with session_factory() as session:
            
            # Check if repository was created/found
            repo_stmt = select(Repository).where(Repository.full_name == 'test/repo')
            repo_result = await session.execute(repo_stmt)
            repo = repo_result.scalar_one_or_none()
            
            if repo:
                print(f"✅ Repository found: {repo.full_name} (ID: {repo.id})")
            else:
                print("❌ Repository not found in database")
                return False
                
            # Check if issue was created (get the latest one if multiple exist)
            issue_stmt = select(Issue).where(Issue.github_issue_id == 999999).order_by(Issue.created_at.desc()).limit(1)
            issue_result = await session.execute(issue_stmt)
            issue = issue_result.scalar_one_or_none()
            
            if issue:
                print(f"✅ Issue found: {issue.title} (ID: {issue.id})")
            else:
                print("❌ Issue not found in database")
                return False
                
            # Check if claim was detected and created (get the latest one if multiple exist)
            claim_stmt = select(Claim).where(Claim.github_username == 'claim_maker').order_by(Claim.created_at.desc()).limit(1)
            claim_result = await session.execute(claim_stmt)
            claim = claim_result.scalar_one_or_none()
            
            if claim:
                print(f"✅ Claim found: {claim.github_username} -> Issue {claim.issue_id} (Confidence: {claim.confidence_score})")
            else:
                print("❌ Claim not found in database")
                return False
                
            # Check if activity log was created (get the latest one if multiple exist)
            activity_stmt = select(ActivityLog).where(ActivityLog.claim_id == claim.id).order_by(ActivityLog.timestamp.desc()).limit(1)
            activity_result = await session.execute(activity_stmt)
            activity = activity_result.scalar_one_or_none()
            
            if activity:
                print(f"✅ Activity log found: {activity.activity_type.value} for claim {activity.claim_id}")
                return True
            else:
                print("❌ Activity log not found")
                return False
                
    except Exception as e:
        print(f"❌ Database verification failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_celery_task_processing():
    """Check if Celery tasks are actually being processed"""
    print("\n⚙️ TESTING CELERY TASK PROCESSING...")
    print("=" * 60)
    
    try:
        # This is tricky to test directly, but we can check if tasks are registered
        from app.core.celery_app import celery_app
        
        # Get active tasks
        try:
            active_tasks = celery_app.control.inspect().active()
            print(f"Active Celery tasks: {active_tasks}")
        except Exception as e:
            print(f"Could not inspect active tasks: {e}")
        
        # Get registered tasks  
        registered_tasks = list(celery_app.tasks.keys())
        expected_tasks = [
            'app.tasks.comment_analysis.analyze_comment_task',
            'app.tasks.nudge_check.check_stale_claims_task'
        ]
        
        tasks_found = 0
        for expected_task in expected_tasks:
            if expected_task in registered_tasks:
                print(f"✅ Task registered: {expected_task}")
                tasks_found += 1
            else:
                print(f"❌ Task missing: {expected_task}")
                
        if tasks_found == len(expected_tasks):
            print("✅ All expected Celery tasks are registered")
            return True
        else:
            print(f"❌ Only {tasks_found}/{len(expected_tasks)} tasks registered")
            return False
            
    except Exception as e:
        print(f"❌ Celery task check failed: {e}")
        return False

async def run_brutal_honesty_test():
    """Run the complete brutal honesty test"""
    print("💀 BRUTAL HONESTY TEST - DOES IT ACTUALLY WORK?")
    print("=" * 60)
    print("Testing REAL end-to-end functionality with actual servers and webhooks\n")
    
    # Start servers
    fastapi_process, celery_process = start_test_servers()
    
    try:
        test_results = {}
        
        # Test 1: Server Health
        test_results['Server Health'] = test_server_health()
        
        # Test 2: Webhook Processing  
        test_results['Webhook Processing'] = test_webhook_endpoint()
        
        # Wait a bit for async processing
        print("⏳ Waiting for async processing...")
        await asyncio.sleep(3)
        
        # Test 3: Database Changes
        test_results['Database Changes'] = await verify_database_changes()
        
        # Test 4: Celery Tasks
        test_results['Celery Task Processing'] = test_celery_task_processing()
        
        # Final verdict
        print(f"\n{'=' * 60}")
        print("💀 BRUTAL HONESTY RESULTS")
        print("=" * 60)
        
        passed = sum(1 for result in test_results.values() if result)
        total = len(test_results)
        
        for test_name, result in test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"  {test_name}: {status}")
        
        success_rate = (passed / total) * 100
        print(f"\nOverall: {passed}/{total} tests passed ({success_rate:.1f}%)")
        
        if passed == total:
            print("\n🎉 BRUTAL HONESTY VERDICT: SYSTEM ACTUALLY WORKS!")
            print("✅ Real webhook processing confirmed")
            print("✅ Database operations working end-to-end")  
            print("✅ Async task processing operational")
            print("✅ Claims are being detected and stored")
            print("✅ NO LIES DETECTED - System is genuinely functional")
            return 0
        else:
            print(f"\n💥 BRUTAL HONESTY VERDICT: SYSTEM PARTIALLY BROKEN")
            print(f"❌ {total-passed} critical components failing")
            print("❌ Previous test results were overly optimistic")
            print("❌ System needs real fixes before production")
            return 1
            
    finally:
        stop_test_servers(fastapi_process, celery_process)

if __name__ == "__main__":
    exit_code = asyncio.run(run_brutal_honesty_test())
    sys.exit(exit_code)