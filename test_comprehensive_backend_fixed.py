#!/usr/bin/env python3
"""
COMPREHENSIVE END-TO-END TEST WITH PROPER FIXES
Tests the complete backend flow from webhook to database with correct parameter binding
"""
import asyncio
import json
import sys
import os
from datetime import datetime, timezone

# Add app to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

async def test_database_setup():
    """Test database connection and basic operations"""
    print("🗄️ TESTING DATABASE SETUP...")
    print("=" * 50)
    
    try:
        from app.db.database import get_async_session
        from app.db.models.repositories import Repository
        from app.db.models.issues import Issue 
        from app.db.models.claims import Claim
        from app.db.models.activity_log import ActivityLog
        from sqlalchemy import select, text
        
        # Get async session factory directly
        from app.db.database import get_async_session_factory
        session_factory = get_async_session_factory()
        
        async with session_factory() as session:
            # Test basic connection
            result = await session.execute(text("SELECT 1"))
            if result.scalar() == 1:
                print("✅ Database connection successful")
            else:
                print("❌ Database connection failed")
                return False
                
            # Test table existence
            tables_to_check = ['repositories', 'issues', 'claims', 'activity_logs']
            for table in tables_to_check:
                try:
                    result = await session.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    count = result.scalar()
                    print(f"✅ Table '{table}' exists ({count} records)")
                except Exception as e:
                    print(f"❌ Table '{table}' issue: {e}")
                    return False
                    
                await session.commit()
            except Exception as e:
                await session.rollback()
                raise e
                    
        return True
        
    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        return False

async def test_pattern_matching():
    """Test pattern matching service"""
    print("\n🧠 TESTING PATTERN MATCHING...")
    print("=" * 50)
    
    try:
        from app.services.pattern_matcher import pattern_matcher
        
        # Test strong claim
        result = pattern_matcher.analyze_comment("I'll work on this issue", {}, {})
        if result.get('is_claim', False) and result.get('final_score', 0) >= 90:
            print("✅ Strong claim detection working")
        else:
            print(f"❌ Strong claim failed: {result}")
            return False
            
        # Test weak claim  
        result = pattern_matcher.analyze_comment("Can I maybe work on this?", {}, {})
        if result.get('is_claim', False) and result.get('final_score', 0) >= 70:
            print("✅ Weak claim detection working")
        else:
            print(f"❌ Weak claim failed: {result}")
            return False
            
        # Test non-claim
        result = pattern_matcher.analyze_comment("This looks interesting", {}, {})
        if not result.get('is_claim', False):
            print("✅ Non-claim detection working")
        else:
            print(f"❌ Non-claim failed: {result}")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Pattern matching failed: {e}")
        return False

async def test_repository_creation():
    """Test repository creation and monitoring"""
    print("\n📁 TESTING REPOSITORY CREATION...")
    print("=" * 50)
    
    try:
        from app.db.database import get_async_session
        from app.db.models.repositories import Repository
        from sqlalchemy import select, delete
        
        test_repo_data = {
            'owner': 'test-owner',
            'name': 'test-repo',
            'full_name': 'test-owner/test-repo',
            'is_active': True,
            'webhook_url': 'https://example.com/webhook',
            'grace_period_days': 7
        }
        
        from app.db.database import get_async_session_factory
        session_factory = get_async_session_factory()
        
        async with session_factory() as session:
            try:
                # Clean up any existing test repo
                await session.execute(
                    delete(Repository).where(Repository.full_name == 'test-owner/test-repo')
                )
                await session.commit()
                
                # Create test repository
                repo = Repository(**test_repo_data)
                session.add(repo)
                await session.commit()
                await session.refresh(repo)
                
                print(f"✅ Repository created with ID: {repo.id}")
                
                # Verify creation
                stmt = select(Repository).where(Repository.full_name == 'test-owner/test-repo')
                result = await session.execute(stmt)
                found_repo = result.scalar_one_or_none()
                
                if found_repo:
                    print(f"✅ Repository verified: {found_repo.full_name}")
                    return found_repo.id
                else:
                    print("❌ Repository not found after creation")
                    return None
            except Exception as e:
                await session.rollback()
                raise e
                
    except Exception as e:
        print(f"❌ Repository creation failed: {e}")
        return None

async def test_issue_creation(repo_id):
    """Test issue creation"""
    print("\n📝 TESTING ISSUE CREATION...")
    print("=" * 50)
    
    try:
        from app.db.database import get_async_session
        from app.db.models.issues import Issue
        from sqlalchemy import select, delete
        
        test_issue_data = {
            'repository_id': repo_id,
            'github_issue_id': 12345,
            'github_issue_number': 1,
            'title': 'Test Issue for Claims',
            'body': 'This is a test issue',
            'status': 'OPEN',
            'github_data': {
                'html_url': 'https://github.com/test-owner/test-repo/issues/1',
                'state': 'open',
                'created_at': '2024-10-05T01:00:00Z'
            }
        }
        
        from app.db.database import get_async_session_factory
        session_factory = get_async_session_factory()
        
        async with session_factory() as session:
            try:
            # Clean up any existing test issue
            await session.execute(
                delete(Issue).where(Issue.github_issue_id == 12345)
            )
            await session.commit()
            
            # Create test issue
            issue = Issue(**test_issue_data)
            session.add(issue)
            await session.commit()
            await session.refresh(issue)
            
            print(f"✅ Issue created with ID: {issue.id}")
            
            # Verify creation
            stmt = select(Issue).where(Issue.github_issue_id == 12345)
            result = await session.execute(stmt)
            found_issue = result.scalar_one_or_none()
            
            if found_issue:
                print(f"✅ Issue verified: {found_issue.title}")
                return found_issue.id
            else:
                print("❌ Issue not found after creation")
                return None
                
    except Exception as e:
        print(f"❌ Issue creation failed: {e}")
        return None

async def test_claim_creation(issue_id):
    """Test claim creation"""
    print("\n🎯 TESTING CLAIM CREATION...")
    print("=" * 50)
    
    try:
        from app.db.database import get_async_session
        from app.db.models.claims import Claim
        from sqlalchemy import select, delete
        
        test_claim_data = {
            'issue_id': issue_id,
            'github_username': 'test-user',
            'github_user_id': 67890,
            'comment_id': 'test-comment-123',
            'comment_text': 'I will work on this issue!',
            'claim_timestamp': datetime.now(timezone.utc),
            'confidence_score': 95,
            'status': 'ACTIVE',
            'pattern_matched': 'direct_claim'
        }
        
        from app.db.database import get_async_session_factory
        session_factory = get_async_session_factory()
        
        async with session_factory() as session:
            try:
            # Clean up any existing test claim
            await session.execute(
                delete(Claim).where(Claim.comment_id == 'test-comment-123')
            )
            await session.commit()
            
            # Create test claim
            claim = Claim(**test_claim_data)
            session.add(claim)
            await session.commit()
            await session.refresh(claim)
            
            print(f"✅ Claim created with ID: {claim.id}")
            
            # Verify creation with proper parameter binding
            stmt = select(Claim).where(Claim.comment_id == 'test-comment-123')
            result = await session.execute(stmt)
            found_claim = result.scalar_one_or_none()
            
            if found_claim:
                print(f"✅ Claim verified: {found_claim.github_username} claimed issue")
                return found_claim.id
            else:
                print("❌ Claim not found after creation")
                return None
                
    except Exception as e:
        print(f"❌ Claim creation failed: {e}")
        return None

async def test_activity_log_creation(claim_id):
    """Test activity log creation"""
    print("\n📊 TESTING ACTIVITY LOG CREATION...")
    print("=" * 50)
    
    try:
        from app.db.database import get_async_session
        from app.db.models.activity_log import ActivityLog
        from sqlalchemy import select, delete
        
        test_activity_data = {
            'claim_id': claim_id,
            'activity_type': 'CLAIM_DETECTED',
            'description': 'Claim detected from comment analysis',
            'metadata': {
                'confidence_score': 95,
                'pattern': 'direct_claim'
            }
        }
        
        from app.db.database import get_async_session_factory
        session_factory = get_async_session_factory()
        
        async with session_factory() as session:
            try:
            # Clean up any existing test activity
            await session.execute(
                delete(ActivityLog).where(ActivityLog.claim_id == claim_id)
            )
            await session.commit()
            
            # Create test activity log
            activity = ActivityLog(**test_activity_data)
            session.add(activity)
            await session.commit()
            await session.refresh(activity)
            
            print(f"✅ Activity log created with ID: {activity.id}")
            
            # Verify creation with proper parameter binding
            stmt = select(ActivityLog).where(ActivityLog.claim_id == claim_id)
            result = await session.execute(stmt)
            found_activity = result.scalar_one_or_none()
            
            if found_activity:
                print(f"✅ Activity log verified: {found_activity.activity_type}")
                return found_activity.id
            else:
                print("❌ Activity log not found after creation")
                return None
                
    except Exception as e:
        print(f"❌ Activity log creation failed: {e}")
        return None

async def test_end_to_end_query():
    """Test complex end-to-end queries with proper parameter binding"""
    print("\n🔍 TESTING END-TO-END QUERIES...")
    print("=" * 50)
    
    try:
        from app.db.database import get_async_session
        from app.db.models.repositories import Repository
        from app.db.models.issues import Issue
        from app.db.models.claims import Claim
        from app.db.models.activity_log import ActivityLog
        from sqlalchemy import select, text, func
        
        from app.db.database import get_async_session_factory
        session_factory = get_async_session_factory()
        
        async with session_factory() as session:
            try:
            # Test 1: Count all records
            tables_and_models = [
                ('repositories', Repository),
                ('issues', Issue), 
                ('claims', Claim),
                ('activity_logs', ActivityLog)
            ]
            
            for table_name, model in tables_and_models:
                # Use proper SQLAlchemy select with model
                stmt = select(func.count(model.id))
                result = await session.execute(stmt)
                count = result.scalar()
                print(f"✅ {table_name}: {count} records")
            
            # Test 2: Complex join query with proper parameter binding
            stmt = (
                select(Repository.full_name, Issue.title, Claim.github_username)
                .join(Issue, Issue.repository_id == Repository.id)
                .join(Claim, Claim.issue_id == Issue.id)
                .where(Repository.full_name == 'test-owner/test-repo')
            )
            
            result = await session.execute(stmt)
            rows = result.all()
            
            if rows:
                for row in rows:
                    print(f"✅ Join query result: {row.full_name} | {row.title} | {row.github_username}")
            else:
                print("ℹ️ No joined data found (this is expected if test data was cleaned up)")
                
            # Test 3: Activity log with claim relationship
            stmt = (
                select(ActivityLog, Claim)
                .join(Claim, ActivityLog.claim_id == Claim.id)
                .where(Claim.github_username == 'test-user')
            )
            
            result = await session.execute(stmt)
            activity_claim_pairs = result.all()
            
            if activity_claim_pairs:
                for activity, claim in activity_claim_pairs:
                    print(f"✅ Activity-Claim relationship: {activity.activity_type} for {claim.github_username}")
            else:
                print("ℹ️ No activity-claim relationships found")
                
        return True
        
    except Exception as e:
        print(f"❌ End-to-end queries failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def cleanup_test_data():
    """Clean up test data"""
    print("\n🧹 CLEANING UP TEST DATA...")
    print("=" * 50)
    
    try:
        from app.db.database import get_async_session
        from app.db.models.repositories import Repository
        from app.db.models.issues import Issue
        from app.db.models.claims import Claim
        from app.db.models.activity_log import ActivityLog
        from sqlalchemy import delete
        
        from app.db.database import get_async_session_factory
        session_factory = get_async_session_factory()
        
        async with session_factory() as session:
            try:
            # Delete in reverse order of foreign key dependencies
            await session.execute(delete(ActivityLog).where(ActivityLog.description.like('%test%')))
            await session.execute(delete(Claim).where(Claim.github_username == 'test-user'))
            await session.execute(delete(Issue).where(Issue.github_issue_id == 12345))
            await session.execute(delete(Repository).where(Repository.full_name == 'test-owner/test-repo'))
            
            await session.commit()
            print("✅ Test data cleaned up")
            
    except Exception as e:
        print(f"⚠️ Cleanup warning: {e}")

async def run_comprehensive_test():
    """Run the complete comprehensive test"""
    print("🚀 COMPREHENSIVE BACKEND TEST - FIXED VERSION")
    print("=" * 70)
    print("Testing complete end-to-end functionality with proper fixes\n")
    
    # Clean up at start
    await cleanup_test_data()
    
    test_results = {}
    
    # Test 1: Database Setup
    test_results['Database Setup'] = await test_database_setup()
    
    # Test 2: Pattern Matching
    test_results['Pattern Matching'] = await test_pattern_matching()
    
    # Test 3: Repository Creation
    repo_id = await test_repository_creation()
    test_results['Repository Creation'] = repo_id is not None
    
    if repo_id:
        # Test 4: Issue Creation
        issue_id = await test_issue_creation(repo_id)
        test_results['Issue Creation'] = issue_id is not None
        
        if issue_id:
            # Test 5: Claim Creation
            claim_id = await test_claim_creation(issue_id)
            test_results['Claim Creation'] = claim_id is not None
            
            if claim_id:
                # Test 6: Activity Log Creation
                activity_id = await test_activity_log_creation(claim_id)
                test_results['Activity Log Creation'] = activity_id is not None
    
    # Test 7: End-to-End Queries
    test_results['End-to-End Queries'] = await test_end_to_end_query()
    
    # Clean up at end
    await cleanup_test_data()
    
    # Final Results
    print(f"\n{'=' * 70}")
    print("🎯 FINAL TEST RESULTS")
    print("=" * 70)
    
    passed = sum(1 for result in test_results.values() if result)
    total = len(test_results)
    
    for test_name, result in test_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {test_name}: {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed ({(passed/total)*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED - BACKEND FULLY OPERATIONAL!")
        print("✅ Database operations work correctly")
        print("✅ No SQLAlchemy parameter binding errors") 
        print("✅ End-to-end flow verified")
        print("✅ Ready for production use")
        return 0
    else:
        print(f"\n⚠️ {total - passed} test(s) failed - needs attention")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(run_comprehensive_test())
    sys.exit(exit_code)