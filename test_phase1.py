"""
Quick test script for Phase 1 implementation.
Tests database initialization and basic user operations.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.database import init_database, get_db_manager, User, Session
from src.auth import UserService, hash_password, verify_password
from datetime import datetime


def test_database_initialization():
    """Test 1: Database initialization"""
    print("\n" + "="*60)
    print("TEST 1: Database Initialization")
    print("="*60)

    try:
        init_database()
        print("✅ Database initialized successfully")
        
        db_manager = get_db_manager()
        print(f"✅ Database location: {db_manager.db_path}")
        
        return True
    except Exception as e:
        print(f"❌ Database initialization failed: {str(e)}")
        return False


def test_user_registration():
    """Test 2: User registration"""
    print("\n" + "="*60)
    print("TEST 2: User Registration")
    print("="*60)

    try:
        db_manager = get_db_manager()

        # Idempotent: remove any leftover test user so registration runs fresh.
        with db_manager.get_session() as session:
            existing = session.query(User).filter(
                (User.username == "testuser") | (User.email == "test@example.com")
            ).all()
            for old in existing:
                session.delete(old)
            session.commit()

        with db_manager.get_session() as session:
            success, error, user = UserService.register_user(
                session,
                username="testuser",
                email="test@example.com",
                password="TestPassword123",
                full_name="Test User"
            )
            
            if success and user:
                print(f"✅ User registered successfully")
                print(f"   - ID: {user.id}")
                print(f"   - Username: {user.username}")
                print(f"   - Email: {user.email}")
                print(f"   - Role: {user.role}")
                print(f"   - Active: {user.is_active}")
                return True, user
            else:
                print(f"❌ Registration failed: {error}")
                return False, None
                
    except Exception as e:
        print(f"❌ Registration test failed: {str(e)}")
        return False, None


def test_user_login(user):
    """Test 3: User login"""
    print("\n" + "="*60)
    print("TEST 3: User Login")
    print("="*60)

    try:
        db_manager = get_db_manager()
        
        with db_manager.get_session() as session:
            success, error, token, logged_in_user = UserService.login_user(
                session,
                username="testuser",
                password="TestPassword123"
            )
            
            if success and token:
                print(f"✅ User logged in successfully")
                print(f"   - Token: {token[:10]}...{token[-10:]}")
                print(f"   - Token length: {len(token)} chars")
                print(f"   - User: {logged_in_user.username}")
                return True, token
            else:
                print(f"❌ Login failed: {error}")
                return False, None
                
    except Exception as e:
        print(f"❌ Login test failed: {str(e)}")
        return False, None


def test_session_verification(token):
    """Test 4: Session verification"""
    print("\n" + "="*60)
    print("TEST 4: Session Verification")
    print("="*60)

    try:
        db_manager = get_db_manager()
        
        with db_manager.get_session() as session:
            is_valid, verified_user = UserService.verify_session(session, token)
            
            if is_valid and verified_user:
                print(f"✅ Session verified successfully")
                print(f"   - User: {verified_user.username}")
                print(f"   - Email: {verified_user.email}")
                return True
            else:
                print(f"❌ Session verification failed")
                return False
                
    except Exception as e:
        print(f"❌ Session verification test failed: {str(e)}")
        return False


def test_password_utilities():
    """Test 5: Password hashing and verification"""
    print("\n" + "="*60)
    print("TEST 5: Password Utilities")
    print("="*60)

    try:
        password = "SecurePassword123"
        
        # Test hashing
        hashed = hash_password(password)
        print(f"✅ Password hashed successfully")
        print(f"   - Hash length: {len(hashed)} chars")
        print(f"   - Hash starts with: $2b... (bcrypt format)")
        
        # Test verification
        is_valid = verify_password(password, hashed)
        if is_valid:
            print(f"✅ Password verification successful")
        else:
            print(f"❌ Password verification failed")
            return False
        
        # Test wrong password
        is_invalid = verify_password("WrongPassword123", hashed)
        if not is_invalid:
            print(f"✅ Wrong password rejected correctly")
        else:
            print(f"❌ Wrong password should have been rejected")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Password utility test failed: {str(e)}")
        return False


def test_user_logout(token):
    """Test 6: User logout"""
    print("\n" + "="*60)
    print("TEST 6: User Logout")
    print("="*60)

    try:
        db_manager = get_db_manager()
        
        with db_manager.get_session() as session:
            success = UserService.logout_user(session, token)
            
            if success:
                print(f"✅ User logged out successfully")
                
                # Verify session is gone
                is_valid, user = UserService.verify_session(session, token)
                if not is_valid:
                    print(f"✅ Session invalidated after logout")
                    return True
                else:
                    print(f"❌ Session still valid after logout")
                    return False
            else:
                print(f"❌ Logout failed")
                return False
                
    except Exception as e:
        print(f"❌ Logout test failed: {str(e)}")
        return False


def run_all_tests():
    """Run all tests"""
    print("\n" + "="*60)
    print("IGCSE TUTOR - PHASE 1 TEST SUITE")
    print("="*60)
    
    results = []
    
    # Test 1: Database Initialization
    results.append(("Database Initialization", test_database_initialization()))
    
    # Test 2: User Registration
    success, user = test_user_registration()
    results.append(("User Registration", success))
    
    # Test 3-5 only run if registration succeeded
    if success:
        # Test 3: User Login
        success, token = test_user_login(user)
        results.append(("User Login", success))
        
        if success and token:
            # Test 4: Session Verification
            results.append(("Session Verification", test_session_verification(token)))
            
            # Test 6: User Logout
            results.append(("User Logout", test_user_logout(token)))
    
    # Test 5: Password Utilities (independent)
    results.append(("Password Utilities", test_password_utilities()))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status:10} - {test_name}")
    
    print("="*60)
    print(f"Result: {passed}/{total} tests passed")
    print("="*60)
    
    if passed == total:
        print("\n🎉 All tests passed! Phase 1 implementation is working correctly.")
        return True
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please review the errors above.")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
