#!/usr/bin/env python3
"""
FRESH BRUTAL HONESTY TEST - NEW IDs TO VERIFY IT'S REALLY WORKING
"""
import asyncio
import json
import sys
import os
import requests
import time
import subprocess
import random
from datetime import datetime, timezone

# Add app to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def start_test_servers():
    """Start servers with fresh processes"""
    print("🚀 STARTING FRESH TEST SERVERS...")
    print("=" * 60)
    
    # Kill any existing processes
    subprocess.run(['pkill', '-f', 'uvicorn'], capture_output=True)
    subprocess.run(['pkill', '-f', 'celery'], capture_output=True)
    time.sleep(2)
    
    # Start FastAPI server
    print("Starting FastAPI server...")
    fastapi_process = subprocess.Popen([
        'python3', '-m', 'uvicorn', 'app.main:app', 
        '--host', '0.0.0.0', '--port', '8001', '--reload'
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Start Celery worker
    print("Starting Celery worker...")
    celery_process = subprocess.Popen([
        'python3', '-m', 'celery', '-A', 'app.core.celery_app', 'worker',
        '--loglevel=info', '--pool=solo'
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Wait for servers to start
    print("Waiting for servers to initialize...")
    time.sleep(8)
    
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

def test_fresh_webhook():
    """Test with completely fresh unique IDs"""
    print("\n🔗 TESTING FRESH WEBHOOK WITH NEW IDs...")
    print("=" * 60)
    
    # Generate completely unique IDs
    unique_suffix = int(time.time())
    repo_id = 800000 + unique_suffix
    issue_id = 900000 + unique_suffix  
    comment_id = 1000000 + unique_suffix
    issue_number = random.randint(100, 999)
    
    payload = {
        "action": "created",
        "issue": {
            "id": issue_id,
            "number": issue_number,
            "title": f"Fresh test issue {unique_suffix}",
            "body": f"Fresh test for verification {unique_suffix}",
            "state": "open",
            "html_url": f"https://github.com/fresh/test{unique_suffix}/issues/{issue_number}",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "user": {
                "login": "fresh_creator",
                "id": 20000 + unique_suffix
            }
        },
        "comment": {
            "id": comment_id,
            "body": f"I'll work on this fresh issue {unique_suffix}!",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "html_url": f"https://github.com/fresh/test{unique_suffix}/issues/{issue_number}#issuecomment-{comment_id}",
            "user": {
                "login": f"fresh_claimer_{unique_suffix}",
                "id": 30000 + unique_suffix
            }
        },
        "repository": {
            "id": repo_id,
            "name": f"test-repo-{unique_suffix}",
            "full_name": f"fresh/test{unique_suffix}",
            "owner": {
                "login": "fresh",
                "id": 40000 + unique_suffix
            },
            "html_url": f"https://github.com/fresh/test{unique_suffix}"
        }
    }
    
    print(f"Testing with unique IDs: repo={repo_id}, issue={issue_id}, comment={comment_id}")
    
    try:
        response = requests.post(
            'http://localhost:8001/api/v1/webhooks/github',
            json=payload,
            headers={
                'Content-Type': 'application/json',
                'X-GitHub-Event': 'issue_comment'
            },
            timeout=30
        )
        
        print(f"Webhook response status: {response.status_code}")
        print(f"Webhook response body: {response.text}")
        
        if response.status_code == 200:
            print("✅ Fresh webhook accepted!")
            return payload
        else:
            print("❌ Fresh webhook failed!")
            return None
            
    except Exception as e:
        print(f"❌ Fresh webhook error: {e}")
        return None

async def verify_fresh_database_changes(payload):
    """Verify the fresh webhook actually created database records"""
    print("\n🗄️ VERIFYING FRESH DATABASE CHANGES...")
    print("=" * 60)
    
    if not payload:
        return False
        
    try:
        from app.db.database import get_async_session_factory
        from app.db.models.repositories import Repository
        from app.db.models.issues import Issue  
        from app.db.models.claims import Claim
        from app.db.models.activity_log import ActivityLog
        from sqlalchemy import select
        
        repo_id = payload['repository']['id']
        issue_id = payload['issue']['id'] 
        username = payload['comment']['user']['login']
        
        session_factory = get_async_session_factory()
        async with session_factory() as session:
            
            # Check if fresh repository was created
            repo_stmt = select(Repository).where(Repository.github_repo_id == repo_id)
            repo_result = await session.execute(repo_stmt)
            repo = repo_result.scalar_one_or_none()
            
            if repo:
                print(f"✅ Fresh repository found: {repo.full_name} (DB ID: {repo.id}, GitHub ID: {repo_id})")
            else:
                print(f"❌ Fresh repository not found (GitHub ID: {repo_id})")
                return False
                
            # Check if fresh issue was created
            issue_stmt = select(Issue).where(Issue.github_issue_id == issue_id)
            issue_result = await session.execute(issue_stmt)
            issue = issue_result.scalar_one_or_none()
            
            if issue:
                print(f"✅ Fresh issue found: {issue.title} (DB ID: {issue.id}, GitHub ID: {issue_id})")
            else:
                print(f"❌ Fresh issue not found (GitHub ID: {issue_id})")
                return False
                
            # Check if fresh claim was created
            claim_stmt = select(Claim).where(Claim.github_username == username)
            claim_result = await session.execute(claim_stmt)
            claim = claim_result.scalar_one_or_none()
            
            if claim:
                print(f"✅ Fresh claim found: {claim.github_username} -> Issue {claim.issue_id} (Confidence: {claim.confidence_score})")
            else:
                print(f"❌ Fresh claim not found for user: {username}")
                return False
                
            # Check if fresh activity log was created
            activity_stmt = select(ActivityLog).where(ActivityLog.claim_id == claim.id)
            activity_result = await session.execute(activity_stmt)
            activity = activity_result.scalar_one_or_none()
            
            if activity:
                print(f"✅ Fresh activity log found: {activity.activity_type.value} for claim {activity.claim_id}")
                return True
            else:
                print("❌ Fresh activity log not found")
                return False
                
    except Exception as e:
        print(f"❌ Fresh database verification failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def run_fresh_brutal_test():
    """Run the fresh brutal honesty test with new data"""
    print("💀 FRESH BRUTAL HONESTY TEST - COMPLETELY NEW DATA")
    print("=" * 70)
    print("Testing with brand new unique IDs to verify real functionality\n")
    
    # Start servers
    fastapi_process, celery_process = start_test_servers()
    
    try:
        # Test server health
        try:
            health_response = requests.get('http://localhost:8001/health', timeout=5)
            server_health = health_response.status_code == 200
            if server_health:
                print("✅ Fresh server is running")
            else:
                print("❌ Fresh server not responding")
        except:
            print("❌ Fresh server not accessible")
            server_health = False
        
        # Test fresh webhook
        fresh_payload = test_fresh_webhook()
        webhook_success = fresh_payload is not None
        
        # Wait for processing
        print("⏳ Waiting for fresh processing...")
        await asyncio.sleep(5)
        
        # Verify fresh database changes
        db_success = await verify_fresh_database_changes(fresh_payload)
        
        # Final verdict
        print(f"\n{'=' * 70}")
        print("💀 FRESH BRUTAL HONESTY RESULTS")
        print("=" * 70)
        
        results = {
            'Server Health': server_health,
            'Fresh Webhook Processing': webhook_success,
            'Fresh Database Changes': db_success
        }
        
        passed = sum(1 for result in results.values() if result)
        total = len(results)
        
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"  {test_name}: {status}")
        
        success_rate = (passed / total) * 100
        print(f"\nOverall: {passed}/{total} tests passed ({success_rate:.1f}%)")
        
        if passed == total:
            print("\n🎉 FRESH BRUTAL HONESTY VERDICT: SYSTEM REALLY WORKS!")
            print("✅ Fresh webhook processed and stored in database")
            print("✅ New unique records created successfully")  
            print("✅ End-to-end flow confirmed with fresh data")
            print("✅ NO CACHED RESULTS - System genuinely functional")
            return 0
        else:
            print(f"\n💥 FRESH BRUTAL HONESTY VERDICT: SYSTEM BROKEN")
            print(f"❌ {total-passed} components failing with fresh data")
            return 1
            
    finally:
        stop_test_servers(fastapi_process, celery_process)

if __name__ == "__main__":
    exit_code = asyncio.run(run_fresh_brutal_test())
    sys.exit(exit_code)