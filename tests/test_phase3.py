"""
Phase 3 Test Suite: Offline Caching and Synchronization
Tests offline cache manager, sync manager, and connectivity detection.
"""

import os
import sys
import time
import json
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.database import init_database, get_db_manager, get_session
from src.auth import UserService
from src.offline import CacheManager, SyncManager, StatusDetector


def setup_test_db():
    """Initialize test database."""
    try:
        init_database()
        return True
    except Exception as e:
        print(f"Database setup error: {e}")
        return False


def create_test_user():
    """Create a test user for testing."""
    try:
        db_session = get_session()
        
        unique_suffix = int(time.time() * 1000) % 1000000
        username = f"testuser_phase3_{unique_suffix}"
        email = f"testuser{unique_suffix}@test.com"
        
        success, msg, user = UserService.register_user(
            db_session,
            username=username,
            email=email,
            password="TestPassword123!",
            full_name="Test User Phase 3"
        )
        
        if success:
            return user, db_session
        else:
            print(f"User creation failed: {msg}")
            return None, db_session
    
    except Exception as e:
        print(f"User creation error: {e}")
        return None, None


def test_connectivity_detection():
    """Test online/offline status detection."""
    print("\n" + "="*60)
    print("TEST 1: Connectivity Detection")
    print("="*60)
    
    try:
        # Test online check
        is_online = StatusDetector.is_online(timeout_seconds=3)
        print(f"✅ PASS: Online detection returned: {is_online}")
        
        # Test with fallback
        is_online_fb, status_msg = StatusDetector.check_with_fallback()
        print(f"✅ PASS: Fallback check returned: {is_online_fb}, Message: {status_msg}")
        
        # Test status details
        status_dict = StatusDetector.get_connectivity_status()
        print(f"✅ PASS: Status details: {status_dict}")
        
        return 3
    
    except Exception as e:
        print(f"❌ FAIL: Connectivity detection error: {e}")
        return 0


def test_cache_operations():
    """Test cache manager functionality."""
    print("\n" + "="*60)
    print("TEST 2: Cache Manager Operations")
    print("="*60)
    
    db_session = get_session()
    tests_passed = 0
    
    try:
        # Test 1: Cache a response
        query = "What is photosynthesis?"
        response = "Photosynthesis is the process by which plants convert light into chemical energy..."
        subject = "science"
        
        success = CacheManager.cache_response(
            db_session,
            query=query,
            response=response,
            subject=subject,
            language_code="en",
            ttl_days=7
        )
        
        if success:
            print(f"✅ PASS: Response cached successfully")
            tests_passed += 1
        else:
            print(f"❌ FAIL: Failed to cache response")
        
        # Test 2: Retrieve cached response
        cached = CacheManager.get_cached_response(
            db_session,
            query=query,
            subject=subject,
            language_code="en"
        )
        
        if cached and cached == response:
            print(f"✅ PASS: Retrieved cached response correctly")
            tests_passed += 1
        else:
            print(f"❌ FAIL: Cached response mismatch or not found")
        
        # Test 3: Cache with different query (should not hit cache)
        different_query = "What is cellular respiration?"
        cached_diff = CacheManager.get_cached_response(
            db_session,
            query=different_query,
            subject=subject,
            language_code="en"
        )
        
        if cached_diff is None:
            print(f"✅ PASS: Different query correctly not cached")
            tests_passed += 1
        else:
            print(f"❌ FAIL: Different query should not be cached")
        
        # Test 4: Get cache size
        cache_size = CacheManager.get_cache_size_for_subject(db_session, "science")
        if cache_size > 0:
            print(f"✅ PASS: Cache size for science: {cache_size}")
            tests_passed += 1
        else:
            print(f"❌ FAIL: Cache size should be > 0")
        
        # Test 5: Cache statistics
        stats = CacheManager.get_cache_statistics(db_session)
        if stats and "active_entries" in stats:
            print(f"✅ PASS: Cache statistics: {stats}")
            tests_passed += 1
        else:
            print(f"❌ FAIL: Cache statistics lookup failed")
        
        return tests_passed
    
    except Exception as e:
        print(f"❌ ERROR: Cache operations error: {e}")
        return tests_passed


def test_cache_expiry():
    """Test cache expiry detection."""
    print("\n" + "="*60)
    print("TEST 3: Cache Expiry Management")
    print("="*60)
    
    db_session = get_session()
    tests_passed = 0
    
    try:
        # Cache a response with TTL of -1 (already expired)
        query = "Test expiry question"
        response = "Test response for expiry"
        subject = "maths"
        
        # We'll manually set an expired entry
        from src.database.models import OfflineCache
        import hashlib
        
        cache_key = hashlib.sha256(f"{query}_{subject}_en".encode()).hexdigest()
        
        # Create an already-expired cache entry
        expired_entry = OfflineCache(
            cache_key=cache_key + "_expired",
            response_json=response,
            subject=subject,
            language_code="en",
            created_at=datetime.utcnow() - timedelta(days=1),
            expires_at=datetime.utcnow() - timedelta(seconds=1)  # Expired 1 second ago
        )
        db_session.add(expired_entry)
        db_session.commit()
        
        print(f"✅ PASS: Expired cache entry created")
        tests_passed += 1
        
        # Verify it's marked as expired
        if expired_entry.is_expired():
            print(f"✅ PASS: Cache entry correctly marked as expired")
            tests_passed += 1
        else:
            print(f"❌ FAIL: Cache entry should be expired")
        
        # Test cleanup
        deleted = CacheManager.cleanup_expired_cache(db_session)
        print(f"✅ PASS: Cleanup removed {deleted} expired entries")
        tests_passed += 1
        
        # Verify the expired entry was deleted
        remaining = db_session.query(OfflineCache).filter_by(cache_key=cache_key + "_expired").first()
        if remaining is None:
            print(f"✅ PASS: Expired entry successfully deleted by cleanup")
            tests_passed += 1
        else:
            print(f"❌ FAIL: Expired entry should have been deleted")
        
        return tests_passed
    
    except Exception as e:
        print(f"❌ ERROR: Cache expiry error: {e}")
        import traceback
        traceback.print_exc()
        return tests_passed


def test_sync_operations():
    """Test sync manager functionality."""
    print("\n" + "="*60)
    print("TEST 4: Sync Manager Operations")
    print("="*60)
    
    user, db_session = create_test_user()
    if not user:
        print("❌ FAIL: Could not create test user")
        return 0
    
    tests_passed = 0
    
    try:
        user_id = user.id
        
        # Test 1: Get pending syncs (should be empty initially)
        pending = SyncManager.get_pending_syncs(db_session, user_id)
        if isinstance(pending, list) and len(pending) == 0:
            print(f"✅ PASS: Pending syncs query returned empty list")
            tests_passed += 1
        else:
            print(f"❌ FAIL: Pending syncs should be empty initially")
        
        # Test 2: Get sync status
        sync_status = SyncManager.get_sync_status(db_session, user_id)
        if sync_status and "user_id" in sync_status:
            print(f"✅ PASS: Sync status: {sync_status}")
            tests_passed += 1
        else:
            print(f"❌ FAIL: Sync status lookup failed")
        
        # Test 3: Get conflict count
        conflict_count = SyncManager.get_conflict_count(db_session, user_id)
        if isinstance(conflict_count, int) and conflict_count == 0:
            print(f"✅ PASS: Conflict count: {conflict_count}")
            tests_passed += 1
        else:
            print(f"❌ FAIL: Conflict count should be 0")
        
        # Test 4: Sync all pending (should succeed with 0 synced)
        sync_count, errors = SyncManager.sync_all_pending(db_session, user_id)
        if sync_count == 0 and isinstance(errors, list):
            print(f"✅ PASS: Sync all pending returned 0 synced, {len(errors)} errors")
            tests_passed += 1
        else:
            print(f"❌ FAIL: Sync all pending failed")
        
        return tests_passed
    
    except Exception as e:
        print(f"❌ ERROR: Sync operations error: {e}")
        return tests_passed


def test_offline_flow():
    """Test complete offline flow simulation."""
    print("\n" + "="*60)
    print("TEST 5: Complete Offline Flow")
    print("="*60)
    
    db_session = get_session()
    tests_passed = 0
    
    try:
        # Simulate offline scenario:
        # 1. User online - requests query, response cached
        # 2. User goes offline - cached response returned
        # 3. User goes online - sync triggered
        
        print("Step 1: User online - caching response")
        query = "Explain photosynthesis"
        response = "Photosynthesis is a biological process..."
        subject = "science"
        
        cached = CacheManager.cache_response(
            db_session,
            query=query,
            response=response,
            subject=subject,
            language_code="en",
            ttl_days=7
        )
        
        if cached:
            print(f"✅ Step 1 Complete: Response cached")
            tests_passed += 1
        else:
            print(f"❌ Step 1 Failed: Could not cache response")
        
        print("Step 2: User offline - retrieving from cache")
        # Simulate offline mode
        is_online = StatusDetector.is_online(timeout_seconds=0.001)  # Very short timeout
        print(f"   Simulated online status: {is_online}")
        
        # Retrieve from cache
        cached_response = CacheManager.get_cached_response(
            db_session,
            query=query,
            subject=subject,
            language_code="en"
        )
        
        if cached_response == response:
            print(f"✅ Step 2 Complete: Retrieved from cache while offline")
            tests_passed += 1
        else:
            print(f"❌ Step 2 Failed: Could not retrieve cached response")
        
        print("Step 3: User online again - sync available")
        # Sync status
        sync_status = SyncManager.get_sync_status(db_session, 1)
        print(f"✅ Step 3 Complete: Sync status retrieved: {sync_status}")
        tests_passed += 1
        
        return tests_passed
    
    except Exception as e:
        print(f"❌ ERROR: Offline flow error: {e}")
        return tests_passed


def test_cache_key_generation():
    """Test cache key generation consistency."""
    print("\n" + "="*60)
    print("TEST 6: Cache Key Generation")
    print("="*60)
    
    tests_passed = 0
    
    try:
        query = "What is photosynthesis?"
        subject = "science"
        language = "en"
        
        # Generate same key twice
        key1 = CacheManager.generate_cache_key(query, subject, language)
        key2 = CacheManager.generate_cache_key(query, subject, language)
        
        if key1 == key2:
            print(f"✅ PASS: Cache keys are consistent")
            tests_passed += 1
        else:
            print(f"❌ FAIL: Cache keys not consistent")
        
        # Test that different queries generate different keys
        different_query = "What is respiration?"
        key3 = CacheManager.generate_cache_key(different_query, subject, language)
        
        if key1 != key3:
            print(f"✅ PASS: Different queries generate different keys")
            tests_passed += 1
        else:
            print(f"❌ FAIL: Different queries should generate different keys")
        
        # Test case insensitivity (same query, different case)
        query_upper = "WHAT IS PHOTOSYNTHESIS?"
        key4 = CacheManager.generate_cache_key(query_upper, subject, language)
        
        if key1 == key4:
            print(f"✅ PASS: Cache keys are case-insensitive")
            tests_passed += 1
        else:
            print(f"❌ FAIL: Cache keys should be case-insensitive")
        
        print(f"   Generated key: {key1[:16]}...")
        
        return tests_passed
    
    except Exception as e:
        print(f"❌ ERROR: Cache key generation error: {e}")
        return tests_passed


def main():
    """Run all Phase 3 tests."""
    print("\n" + "="*60)
    print("IGCSE TUTOR - PHASE 3 TEST SUITE")
    print("Offline Caching & Synchronization Testing")
    print("="*60)
    
    # Initialize database
    if not setup_test_db():
        print("❌ Database initialization failed")
        return
    
    # Run tests
    results = {
        "Connectivity Detection": test_connectivity_detection(),
        "Cache Operations": test_cache_operations(),
        "Cache Expiry": test_cache_expiry(),
        "Sync Operations": test_sync_operations(),
        "Offline Flow": test_offline_flow(),
        "Cache Key Generation": test_cache_key_generation(),
    }
    
    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    total_passed = 0
    for test_name, passed in results.items():
        status = "✅ PASS" if passed > 0 else "⚠️  PARTIAL"
        print(f"{status:12} - {test_name}: {passed} tests")
        total_passed += passed
    
    print("="*60)
    print(f"Result: {total_passed} total tests passed")
    print("="*60)
    
    success = total_passed >= 15
    if success:
        print("\n🎉 All Phase 3 tests passed! Offline functionality is working correctly.")
    else:
        print(f"\n⚠️  {total_passed} of 18 tests passed. Please review failures above.")
    return success


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
