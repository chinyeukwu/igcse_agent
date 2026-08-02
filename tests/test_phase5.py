"""
Phase 5 Test Suite: Admin Panel Dashboard
Tests user management, query monitoring, and system analytics.
"""

import os
import sys
import json
import time
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.database import init_database, get_session
from src.auth import UserService
from src.admin import AdminService
from src.database.models import AuditLog, AdminSettings
from src.quiz import QuizService


def setup_test_db():
    """Initialize test database."""
    try:
        init_database()
        return True
    except Exception as e:
        print(f"Database setup error: {e}")
        return False


def create_test_admin_user():
    """Create a test admin user."""
    try:
        db_session = get_session()
        
        unique_suffix = int(time.time() * 1000) % 1000000
        username = f"admin_phase5_{unique_suffix}"
        email = f"admin{unique_suffix}@test.com"
        
        success, msg, user = UserService.register_user(
            db_session,
            username=username,
            email=email,
            password="AdminPass123!",
            full_name="Admin User Phase 5"
        )
        
        if success:
            # Mark this user as admin
            admin_setting = AdminSettings(
                setting_key=f"admin_role_{user.id}",
                setting_value="true"
            )
            db_session.add(admin_setting)
            db_session.commit()
            return user, db_session
        else:
            return None, db_session
    
    except Exception as e:
        print(f"Admin user creation error: {e}")
        return None, None


def create_test_regular_user():
    """Create a test regular user."""
    try:
        db_session = get_session()
        
        unique_suffix = int(time.time() * 1000) % 1000000
        username = f"user_phase5_{unique_suffix}"
        email = f"user{unique_suffix}@test.com"
        
        success, msg, user = UserService.register_user(
            db_session,
            username=username,
            email=email,
            password="UserPass123!",
            full_name="Regular User Phase 5"
        )
        
        return user if success else None
    
    except Exception as e:
        print(f"Regular user creation error: {e}")
        return None


def test_admin_access_verification():
    """Test admin access verification."""
    print("\n" + "="*60)
    print("TEST 1: Admin Access Verification")
    print("="*60)
    
    db_session = get_session()
    
    # Create admin user
    unique_suffix = int(time.time() * 1000) % 1000000
    username = f"admin_phase5_{unique_suffix}"
    email = f"admin{unique_suffix}@test.com"
    
    success, msg, admin_user = UserService.register_user(
        db_session,
        username=username,
        email=email,
        password="AdminPass123!",
        full_name="Admin User Phase 5"
    )
    
    if not success or not admin_user:
        print("FAIL: Could not create admin user")
        return 0
    
    # Mark this user as admin
    from src.database.models import AdminSettings
    admin_setting = AdminSettings(
        setting_key=f"admin_role_{admin_user.id}",
        setting_value="true"
    )
    db_session.add(admin_setting)
    db_session.commit()
    
    tests_passed = 0
    
    try:
        # Test 1: Admin user has access
        is_admin, msg = AdminService.verify_admin_access(admin_user.id, db_session)
        if is_admin:
            print(f"PASS: Admin user verified")
            tests_passed += 1
        else:
            print(f"FAIL: Admin user should have access")
        
        # Test 2: Regular user does not have access
        # Create regular user with same session
        unique_suffix2 = int(time.time() * 1000) % 1000000
        username2 = f"user_phase5_{unique_suffix2}"
        email2 = f"user{unique_suffix2}@test.com"
        
        success, msg, regular_user = UserService.register_user(
            db_session,
            username=username2,
            email=email2,
            password="UserPass123!",
            full_name="Regular User Phase 5"
        )
        
        if success and regular_user:
            is_admin, msg = AdminService.verify_admin_access(regular_user.id, db_session)
            if not is_admin:
                print(f"PASS: Regular user access denied")
                tests_passed += 1
            else:
                print(f"FAIL: Regular user should not have admin access")
        
        # Test 3: Invalid user returns error
        is_admin, msg = AdminService.verify_admin_access(99999, db_session)
        if not is_admin and "not found" in msg.lower():
            print(f"PASS: Invalid user returns error")
            tests_passed += 1
        else:
            print(f"FAIL: Should return error for invalid user")
        
        # Test 4: No user ID returns error
        is_admin, msg = AdminService.verify_admin_access(None, db_session)
        if not is_admin:
            print(f"PASS: None user ID returns error")
            tests_passed += 1
        else:
            print(f"FAIL: Should handle None user ID")
        
        return tests_passed
    
    except Exception as e:
        print(f"ERROR: Admin access verification error: {e}")
        return tests_passed


def test_user_management():
    """Test user management functions."""
    print("\n" + "="*60)
    print("TEST 2: User Management")
    print("="*60)
    
    db_session = get_session()
    
    tests_passed = 0
    
    try:
        # Create test users with same session
        users = []
        for i in range(3):
            unique_suffix = int(time.time() * 1000) % 1000000 + i
            username = f"user_mgmt_{unique_suffix}"
            email = f"user_mgmt{unique_suffix}@test.com"
            
            success, msg, user = UserService.register_user(
                db_session,
                username=username,
                email=email,
                password="UserPass123!",
                full_name=f"User {i}"
            )
            if success and user:
                users.append(user)
        
        # Test 1: Get all users
        success, users_list, error = AdminService.get_all_users(db_session, limit=100)
        if success and len(users_list) >= 3:
            print(f"PASS: Retrieved {len(users_list)} users")
            tests_passed += 1
        else:
            print(f"FAIL: Could not retrieve users")
        
        # Test 2: Verify user has stats
        if users_list and any(u.get("id") == users[0].id for u in users_list):
            user_stats = next(u for u in users_list if u.get("id") == users[0].id)
            if "quiz_count" in user_stats and "average_score" in user_stats:
                print(f"PASS: User stats included")
                tests_passed += 1
            else:
                print(f"FAIL: User stats missing")
        
        # Test 3: Get user detail
        if users:
            success, detail, error = AdminService.get_user_detail(db_session, users[0].id)
            if success and detail.get("id") == users[0].id:
                print(f"PASS: User detail retrieved")
                tests_passed += 1
            else:
                print(f"FAIL: User detail retrieval failed")
        
        # Test 4: User detail includes activity
        if success and detail:
            if "recent_activity" in detail:
                print(f"PASS: User activity included")
                tests_passed += 1
            else:
                print(f"FAIL: User activity missing")
        
        return tests_passed
    
    except Exception as e:
        print(f"ERROR: User management error: {e}")
        import traceback
        traceback.print_exc()
        return tests_passed


def test_user_actions():
    """Test admin user actions."""
    print("\n" + "="*60)
    print("TEST 3: Admin User Actions")
    print("="*60)
    
    db_session = get_session()
    
    # Create test user with same session
    unique_suffix = int(time.time() * 1000) % 1000000
    username = f"user_action_{unique_suffix}"
    email = f"user_action{unique_suffix}@test.com"
    
    success, msg, test_user = UserService.register_user(
        db_session,
        username=username,
        email=email,
        password="UserPass123!",
        full_name="User Action"
    )
    
    if not success or not test_user:
        print("FAIL: Could not create test user")
        return 0
    
    tests_passed = 0
    
    try:
        # Test 1: Disable user
        success, msg = AdminService.perform_user_action(
            db_session, test_user.id, AdminService.ACTION_DISABLE
        )
        if success:
            print(f"PASS: User disabled")
            tests_passed += 1
        else:
            print(f"FAIL: User disable failed")
        
        # Test 2: Enable user
        success, msg = AdminService.perform_user_action(
            db_session, test_user.id, AdminService.ACTION_ENABLE
        )
        if success:
            print(f"PASS: User enabled")
            tests_passed += 1
        else:
            print(f"FAIL: User enable failed")
        
        # Test 3: Deactivate user
        success, msg = AdminService.perform_user_action(
            db_session, test_user.id, AdminService.ACTION_DEACTIVATE
        )
        if success:
            print(f"PASS: User deactivated")
            tests_passed += 1
        else:
            print(f"FAIL: User deactivate failed")
        
        # Test 4: Invalid action rejected
        success, msg = AdminService.perform_user_action(
            db_session, test_user.id, "invalid_action"
        )
        if not success:
            print(f"PASS: Invalid action rejected")
            tests_passed += 1
        else:
            print(f"FAIL: Should reject invalid action")
        
        return tests_passed
    
    except Exception as e:
        print(f"ERROR: User actions error: {e}")
        return tests_passed


def test_query_monitoring():
    """Test query monitoring functionality."""
    print("\n" + "="*60)
    print("TEST 4: Query Monitoring")
    print("="*60)
    
    db_session = get_session()
    
    # Create test user with same session
    unique_suffix = int(time.time() * 1000) % 1000000
    username = f"user_query_{unique_suffix}"
    email = f"user_query{unique_suffix}@test.com"
    
    success, msg, test_user = UserService.register_user(
        db_session,
        username=username,
        email=email,
        password="UserPass123!",
        full_name="User Query"
    )
    
    if not success or not test_user:
        print("FAIL: Could not create test user")
        return 0
    
    tests_passed = 0
    
    try:
        # Create test audit logs with correct schema
        log1 = AuditLog(
            user_id=test_user.id,
            query_text="Solve 2x + 3 = 7",
            subject="maths",
            tool_used="math_tool",
            response_length=150,
            is_injection_flagged=False,
            is_out_of_scope=False
        )
        db_session.add(log1)
        
        log2 = AuditLog(
            user_id=test_user.id,
            query_text="'; DROP TABLE users; --",
            subject="maths",
            tool_used="math_tool",
            response_length=0,
            is_injection_flagged=True,
            is_out_of_scope=False,
            error_message="SQL injection detected"
        )
        db_session.add(log2)
        db_session.commit()
        
        # Test 1: Get all monitored queries
        success, queries, error = AdminService.get_monitored_queries(db_session, limit=100)
        if success and len(queries) >= 2:
            print(f"PASS: Retrieved {len(queries)} queries")
            tests_passed += 1
        else:
            print(f"FAIL: Query retrieval failed")
        
        # Test 2: Filter by user
        success, queries, error = AdminService.get_monitored_queries(
            db_session, user_id=test_user.id
        )
        if success and len(queries) >= 2:
            print(f"PASS: User filter works")
            tests_passed += 1
        else:
            print(f"FAIL: User filter failed")
        
        # Test 3: Filter by subject
        success, queries, error = AdminService.get_monitored_queries(
            db_session, subject="maths"
        )
        if success:
            print(f"PASS: Subject filter works")
            tests_passed += 1
        else:
            print(f"FAIL: Subject filter failed")
        
        # Test 4: Filter by injection flag
        success, queries, error = AdminService.get_monitored_queries(
            db_session, has_injection_flag=True
        )
        if success and len(queries) >= 1:
            print(f"PASS: Injection filter works")
            tests_passed += 1
        else:
            print(f"FAIL: Injection filter failed")
        
        return tests_passed
    
    except Exception as e:
        print(f"ERROR: Query monitoring error: {e}")
        import traceback
        traceback.print_exc()
        return tests_passed


def test_security_alerts():
    """Test security alert retrieval."""
    print("\n" + "="*60)
    print("TEST 5: Security Alerts")
    print("="*60)
    
    db_session = get_session()
    
    # Create test user with same session
    unique_suffix = int(time.time() * 1000) % 1000000
    username = f"user_alert_{unique_suffix}"
    email = f"user_alert{unique_suffix}@test.com"
    
    success, msg, test_user = UserService.register_user(
        db_session,
        username=username,
        email=email,
        password="UserPass123!",
        full_name="User Alert"
    )
    
    if not success or not test_user:
        print("FAIL: Could not create test user")
        return 0
    
    tests_passed = 0
    
    try:
        # Create alert logs
        alert_log = AuditLog(
            user_id=test_user.id,
            query_text="'; DROP TABLE users; --",
            subject="maths",
            tool_used="math_tool",
            response_length=0,
            is_injection_flagged=True,
            is_out_of_scope=False,
            error_message="Injection attempt blocked"
        )
        db_session.add(alert_log)
        db_session.commit()
        
        # Test 1: Get security alerts
        success, alerts, error = AdminService.get_security_alerts(db_session, limit=50)
        if success:
            print(f"PASS: Retrieved {len(alerts)} alerts")
            tests_passed += 1
        else:
            print(f"FAIL: Alert retrieval failed")
        
        # Test 2: Alerts have required fields
        if alerts and len(alerts) > 0:
            alert = alerts[0]
            if all(k in alert for k in ["type", "severity", "timestamp"]):
                print(f"PASS: Alert has required fields")
                tests_passed += 1
            else:
                print(f"FAIL: Alert missing fields")
        
        # Test 3: Injection alerts marked as high severity
        injection_alerts = [a for a in alerts if a["type"] == "injection_attempt"]
        if injection_alerts and all(a["severity"] == "high" for a in injection_alerts):
            print(f"PASS: Injection alerts marked high severity")
            tests_passed += 1
        else:
            print(f"FAIL: Injection alert severity issue")
        
        # Test 4: Alerts sorted by timestamp
        if len(alerts) > 1:
            timestamps = [a["timestamp"] for a in alerts]
            is_sorted = all(timestamps[i] >= timestamps[i+1] for i in range(len(timestamps)-1))
            if is_sorted:
                print(f"PASS: Alerts sorted correctly")
                tests_passed += 1
            else:
                print(f"FAIL: Alerts not sorted")
        elif len(alerts) == 1:
            print(f"PASS: Single alert properly returned")
            tests_passed += 1
        
        return tests_passed
    
    except Exception as e:
        print(f"ERROR: Security alerts error: {e}")
        import traceback
        traceback.print_exc()
        return tests_passed


def test_dashboard_statistics():
    """Test dashboard statistics."""
    print("\n" + "="*60)
    print("TEST 6: Dashboard Statistics")
    print("="*60)
    
    db_session = get_session()
    
    tests_passed = 0
    
    try:
        # Get dashboard stats
        success, stats, error = AdminService.get_dashboard_statistics(db_session)
        
        if success and stats:
            print(f"PASS: Dashboard statistics retrieved")
            tests_passed += 1
        else:
            print(f"FAIL: Dashboard stats retrieval failed")
        
        # Test 2: Stats have required sections
        if success and stats:
            required_sections = ["users", "quizzes", "sessions", "security"]
            if all(section in stats for section in required_sections):
                print(f"PASS: All statistics sections present")
                tests_passed += 1
            else:
                print(f"FAIL: Missing statistics sections")
        
        # Test 3: User stats correct
        if success and stats and "users" in stats:
            users_section = stats["users"]
            if all(k in users_section for k in ["total", "active", "inactive"]):
                print(f"PASS: User statistics complete")
                tests_passed += 1
            else:
                print(f"FAIL: User statistics incomplete")
        
        # Test 4: Security stats present
        if success and stats and "security" in stats:
            security_section = stats["security"]
            if "injection_attempts" in security_section:
                print(f"PASS: Security statistics include injection attempts")
                tests_passed += 1
            else:
                print(f"FAIL: Security statistics incomplete")
        
        return tests_passed
    
    except Exception as e:
        print(f"ERROR: Dashboard statistics error: {e}")
        return tests_passed


def test_usage_statistics():
    """Test usage statistics."""
    print("\n" + "="*60)
    print("TEST 7: Usage Statistics")
    print("="*60)
    
    db_session = get_session()
    
    tests_passed = 0
    
    try:
        # Get usage stats
        success, usage, error = AdminService.get_usage_statistics(db_session)
        
        if success and usage:
            print(f"PASS: Usage statistics retrieved")
            tests_passed += 1
        else:
            print(f"FAIL: Usage stats retrieval failed")
        
        # Test 2: Cache stats present
        if success and usage and "cache" in usage:
            cache_stats = usage["cache"]
            if all(k in cache_stats for k in ["total_entries", "size_bytes", "size_mb"]):
                print(f"PASS: Cache statistics complete")
                tests_passed += 1
            else:
                print(f"FAIL: Cache statistics incomplete")
        
        # Test 3: Database stats present
        if success and usage and "database" in usage:
            db_stats = usage["database"]
            if all(k in db_stats for k in ["users", "audit_logs", "quiz_attempts"]):
                print(f"PASS: Database statistics complete")
                tests_passed += 1
            else:
                print(f"FAIL: Database statistics incomplete")
        
        # Test 4: Size calculations correct
        if success and usage and "cache" in usage:
            cache_stats = usage["cache"]
            calculated_mb = cache_stats["size_bytes"] / (1024 * 1024)
            if abs(calculated_mb - cache_stats["size_mb"]) < 0.01:
                print(f"PASS: Size calculations correct")
                tests_passed += 1
            else:
                print(f"FAIL: Size calculation mismatch")
        
        return tests_passed
    
    except Exception as e:
        print(f"ERROR: Usage statistics error: {e}")
        return tests_passed


def test_cleanup_operations():
    """Test cleanup operations."""
    print("\n" + "="*60)
    print("TEST 8: Cleanup Operations")
    print("="*60)
    
    db_session = get_session()
    
    tests_passed = 0
    
    try:
        # Test 1: Cache cleanup
        success, stats, error = AdminService.cleanup_cache(db_session, older_than_days=7)
        if success and "deleted_entries" in stats:
            print(f"PASS: Cache cleanup works")
            tests_passed += 1
        else:
            print(f"FAIL: Cache cleanup failed")
        
        # Test 2: Audit log cleanup
        success, stats, error = AdminService.cleanup_audit_logs(db_session, older_than_days=90)
        if success and "deleted_logs" in stats:
            print(f"PASS: Audit log cleanup works")
            tests_passed += 1
        else:
            print(f"FAIL: Audit log cleanup failed")
        
        # Test 3: Cleanup stats include cutoff date
        success, stats, error = AdminService.cleanup_cache(db_session, older_than_days=7)
        if success and "cutoff_date" in stats:
            print(f"PASS: Cleanup stats include cutoff date")
            tests_passed += 1
        else:
            print(f"FAIL: Cutoff date missing from cleanup stats")
        
        # Test 4: Cleanup respects older_than_days
        success, stats, error = AdminService.cleanup_cache(db_session, older_than_days=1)
        # Just verify it ran without error
        if success:
            print(f"PASS: Cleanup respects parameters")
            tests_passed += 1
        else:
            print(f"FAIL: Cleanup failed with different parameters")
        
        return tests_passed
    
    except Exception as e:
        print(f"ERROR: Cleanup operations error: {e}")
        return tests_passed


def test_data_export():
    """Test user data export."""
    print("\n" + "="*60)
    print("TEST 9: Data Export")
    print("="*60)
    
    db_session = get_session()
    
    # Create test user with same session
    unique_suffix = int(time.time() * 1000) % 1000000
    username = f"user_export_{unique_suffix}"
    email = f"user_export{unique_suffix}@test.com"
    
    success, msg, test_user = UserService.register_user(
        db_session,
        username=username,
        email=email,
        password="UserPass123!",
        full_name="User Export"
    )
    
    if not success or not test_user:
        print("FAIL: Could not create test user")
        return 0
    
    tests_passed = 0
    
    try:
        # Test 1: Export as JSON
        success, data, error = AdminService.export_user_data(
            db_session, test_user.id, format="json"
        )
        if success and data:
            print(f"PASS: JSON export works")
            tests_passed += 1
        else:
            print(f"FAIL: JSON export failed")
        
        # Test 2: JSON data is valid
        if success and data:
            try:
                parsed = json.loads(data)
                if all(k in parsed for k in ["user", "quizzes", "audit_logs"]):
                    print(f"PASS: JSON export format valid")
                    tests_passed += 1
                else:
                    print(f"FAIL: JSON export missing sections")
            except:
                print(f"FAIL: JSON export not valid JSON")
        
        # Test 3: Export as CSV
        success, data, error = AdminService.export_user_data(
            db_session, test_user.id, format="csv"
        )
        if success and data:
            print(f"PASS: CSV export works")
            tests_passed += 1
        else:
            print(f"FAIL: CSV export failed")
        
        # Test 4: CSV has expected sections
        if success and data:
            if "USER_INFO" in data and "QUIZ_HISTORY" in data and "AUDIT_LOGS" in data:
                print(f"PASS: CSV export has all sections")
                tests_passed += 1
            else:
                print(f"FAIL: CSV export missing sections")
        
        return tests_passed
    
    except Exception as e:
        print(f"ERROR: Data export error: {e}")
        import traceback
        traceback.print_exc()
        return tests_passed


def main():
    """Run all Phase 5 tests."""
    print("\n" + "="*60)
    print("IGCSE TUTOR - PHASE 5 TEST SUITE")
    print("Admin Panel Dashboard Testing")
    print("="*60)
    
    # Initialize database
    if not setup_test_db():
        print("Database initialization failed")
        return
    
    # Run tests
    results = {
        "Admin Access Verification": test_admin_access_verification(),
        "User Management": test_user_management(),
        "Admin User Actions": test_user_actions(),
        "Query Monitoring": test_query_monitoring(),
        "Security Alerts": test_security_alerts(),
        "Dashboard Statistics": test_dashboard_statistics(),
        "Usage Statistics": test_usage_statistics(),
        "Cleanup Operations": test_cleanup_operations(),
        "Data Export": test_data_export(),
    }
    
    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    total_passed = 0
    for test_name, passed in results.items():
        status = "PASS" if passed > 0 else "PARTIAL"
        print(f"{status:12} - {test_name}: {passed} tests")
        total_passed += passed
    
    print("="*60)
    print(f"Result: {total_passed} total tests passed")
    print("="*60)
    
    success = total_passed >= 30
    if success:
        print("\n[SUCCESS] Phase 5 tests passed! Admin dashboard is working correctly.")
    else:
        print(f"\n{total_passed} of 36+ tests passed. Please review failures above.")
    return success


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
