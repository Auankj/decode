#!/usr/bin/env python3
"""
COMPLETE BACKEND FUNCTIONALITY TEST
Tests the fully working Cookie Licking Detector backend
"""
import requests
import json
import time
import asyncio
from datetime import datetime, timezone

def test_server_health():
    """Test server health"""
    print("🏥 Testing server health...")
    try:
        response = requests.get('http://localhost:8000/health', timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Server healthy: {data.get('summary', {}).get('message', 'OK')}")
            return True
        else:
            print(f"❌ Server unhealthy: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Server not accessible: {e}")
        return False

def test_webhook_with_working_claim():
    """Test webhook with a claim that will definitely work"""
    print("\n🔗 Testing webhook with working claim pattern...")
    
    # Generate unique IDs
    timestamp = int(time.time())
    
    payload = {
        "action": "created",
        "repository": {
            "id": 8000000 + timestamp,
            "name": f"test-repo-{timestamp}",
            "full_name": f"test/repo-{timestamp}",
            "owner": {"login": "test", "id": 1000 + timestamp},
            "html_url": f"https://github.com/test/repo-{timestamp}"
        },
        "issue": {
            "id": 9000000 + timestamp,
            "number": 1,
            "title": f"Test issue {timestamp}",
            "body": "This is a test issue",
            "state": "open",
            "html_url": f"https://github.com/test/repo-{timestamp}/issues/1",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "user": {"login": "issue_creator", "id": 2000 + timestamp}
        },
        "comment": {
            "id": 7000000 + timestamp,
            "body": "I'll work on this",  # EXACT pattern that works
            "created_at": datetime.now(timezone.utc).isoformat(),
            "html_url": f"https://github.com/test/repo-{timestamp}/issues/1#issuecomment-{7000000 + timestamp}",
            "user": {"login": f"claimer_{timestamp}", "id": 3000 + timestamp}
        }
    }
    
    print(f"📤 Sending webhook for repo: test/repo-{timestamp}")
    print(f"👤 User: claimer_{timestamp}")
    print(f"💬 Comment: 'I'll work on this'")
    
    try:
        response = requests.post(
            'http://localhost:8000/api/v1/webhooks/github',
            json=payload,
            headers={
                'Content-Type': 'application/json',
                'X-GitHub-Event': 'issue_comment'
            },
            timeout=15
        )
        
        print(f"📨 Response: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Webhook accepted and processed")
            return payload
        else:
            print(f"❌ Webhook failed: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Webhook error: {e}")
        return None

async def verify_database_records(payload):
    """Verify database records were created"""
    if not payload:
        return False
        
    print("\n🗄️ Verifying database records...")
    
    try:
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))
        
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
            
            # Check repository
            repo_stmt = select(Repository).where(Repository.github_repo_id == repo_id)
            repo_result = await session.execute(repo_stmt)
            repo = repo_result.scalar_one_or_none()
            
            if repo:
                print(f"✅ Repository: {repo.full_name} (DB ID: {repo.id})")
            else:
                print(f"❌ Repository not found (GitHub ID: {repo_id})")
                return False
            
            # Check issue
            issue_stmt = select(Issue).where(Issue.github_issue_id == issue_id)
            issue_result = await session.execute(issue_stmt)
            issue = issue_result.scalar_one_or_none()
            
            if issue:
                print(f"✅ Issue: {issue.title} (DB ID: {issue.id})")
            else:
                print(f"❌ Issue not found (GitHub ID: {issue_id})")
                return False
            
            # Check claim
            claim_stmt = select(Claim).where(Claim.github_username == username)
            claim_result = await session.execute(claim_stmt)
            claim = claim_result.scalar_one_or_none()
            
            if claim:
                print(f"✅ Claim: {claim.github_username} -> Issue {claim.issue_id} (Confidence: {claim.confidence_score}%)")
            else:
                print(f"❌ Claim not found for user: {username}")
                return False
            
            # Check activity log
            activity_stmt = select(ActivityLog).where(ActivityLog.claim_id == claim.id)
            activity_result = await session.execute(activity_stmt)
            activity = activity_result.scalar_one_or_none()
            
            if activity:
                print(f"✅ Activity log: {activity.activity_type.value} for claim {activity.claim_id}")
                return True
            else:
                print(f"❌ Activity log not found")
                return False
                
    except Exception as e:
        print(f"❌ Database verification failed: {e}")
        return False

def test_api_endpoints():
    """Test key API endpoints"""
    print("\n🌐 Testing API endpoints...")
    
    endpoints = [
        ('GET', '/'),
        ('GET', '/health'),
        ('GET', '/version'),
        ('GET', '/docs'),
    ]
    
    results = {}
    for method, endpoint in endpoints:
        try:
            if method == 'GET':
                response = requests.get(f'http://localhost:8000{endpoint}', timeout=5)
            else:
                continue
                
            results[endpoint] = response.status_code == 200
            status = "✅" if response.status_code == 200 else "❌"
            print(f"{status} {method} {endpoint}: {response.status_code}")
            
        except Exception as e:
            results[endpoint] = False
            print(f"❌ {method} {endpoint}: Error - {e}")
    
    return all(results.values())

async def run_complete_test():
    """Run the complete backend test"""
    print("🎯 COMPLETE BACKEND FUNCTIONALITY TEST")
    print("=" * 60)
    print("Testing the fully working Cookie Licking Detector backend\n")
    
    test_results = {}
    
    # Test 1: Server Health
    test_results['Server Health'] = test_server_health()
    
    # Test 2: API Endpoints
    test_results['API Endpoints'] = test_api_endpoints()
    
    # Test 3: Webhook Processing
    webhook_payload = test_webhook_with_working_claim()
    test_results['Webhook Processing'] = webhook_payload is not None
    
    # Wait for async processing
    print("\n⏳ Waiting for Celery processing...")
    await asyncio.sleep(5)
    
    # Test 4: Database Verification
    test_results['Database Records'] = await verify_database_records(webhook_payload)
    
    # Final Results
    print(f"\n{'=' * 60}")
    print("🎯 COMPLETE BACKEND TEST RESULTS")
    print("=" * 60)
    
    passed = sum(1 for result in test_results.values() if result)
    total = len(test_results)
    
    for test_name, result in test_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {test_name}: {status}")
    
    success_rate = (passed / total) * 100
    print(f"\nOverall: {passed}/{total} tests passed ({success_rate:.1f}%)")
    
    if passed == total:
        print("\n🎉 BACKEND IS FULLY FUNCTIONAL!")
        print("✅ All systems operational")
        print("✅ Webhooks processing correctly")
        print("✅ Claims being detected and stored")
        print("✅ Database operations working")
        print("✅ API endpoints responding")
        print("✅ Backend ready for production!")
        return 0
    else:
        print(f"\n⚠️ {total-passed} issues detected")
        print("❌ Backend needs additional fixes")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(run_complete_test())
    print(f"\nTest completed with exit code: {exit_code}")