#!/usr/bin/env python3
"""
Phase 6 Setup and Integration Guide
Quick startup script for admin dashboard and analytics features.
"""

import asyncio
from datetime import datetime
import sys


def print_header(text: str):
    """Print formatted header."""
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")


async def verify_dependencies():
    """Verify all required dependencies are installed."""
    print_header("Verifying Dependencies")
    
    required_packages = [
        "fastapi",
        "streamlit",
        "numpy",
        "scipy",
        "pandas",
        "plotly",
        "jwt",
        "sqlalchemy",
        "redis"
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✓ {package}")
        except ImportError:
            print(f"✗ {package} (MISSING)")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n⚠️  Missing packages: {', '.join(missing_packages)}")
        print("Install them with: pip install -r phase6_requirements.txt")
        return False
    
    print("\n✅ All dependencies installed!")
    return True


async def initialize_database():
    """Initialize database schemas for Phase 6."""
    print_header("Initializing Database")
    
    print("This step requires your database connection to be configured.")
    print("Make sure the following tables exist in your database:")
    
    tables = [
        "audit_logs (admin_id, action, resource, details, timestamp)",
        "security_alerts (user_id, event_type, severity, details, timestamp)",
        "admin_sessions (user_id, token, ip_address, created_at, last_activity)",
        "cache_entries (key, value, expires_at)",
        "activity_logs (user_id, type, timestamp, details)"
    ]
    
    for table in tables:
        print(f"  - {table}")
    
    print("\n💡 Run Alembic migrations or use ORM to create these tables")
    return True


async def configure_security():
    """Configure security settings."""
    print_header("Security Configuration")
    
    print("Update security settings in src/tools/security_utils.py:")
    print("  - Change SECRET_KEY from default")
    print("  - Update database connection strings")
    print("  - Configure MFA settings if needed")
    print("  - Set appropriate token expiration times")
    
    print("\nExample configuration:")
    print("""
    class SecurityConfig:
        SECRET_KEY = "your-long-random-key-here"
        ALGORITHM = "HS256"
        ACCESS_TOKEN_EXPIRE_MINUTES = 30
        MAX_LOGIN_ATTEMPTS = 5
        ADMIN_SESSION_TIMEOUT_MINUTES = 60
    """)
    
    return True


async def setup_api_routes():
    """Guide for setting up API routes."""
    print_header("Setting Up API Routes")
    
    print("Add these routes to your main FastAPI application:\n")
    
    print("src/main.py:")
    print("""
    from fastapi import FastAPI
    from src.api.admin_analytics_routes import (
        get_admin_routes,
        get_analytics_routes
    )
    
    app = FastAPI()
    
    # Include admin and analytics routers
    app.include_router(get_admin_routes())
    app.include_router(get_analytics_routes())
    """)
    
    return True


async def setup_streamlit():
    """Guide for setting up Streamlit dashboards."""
    print_header("Setting Up Streamlit Dashboards")
    
    print("Run the admin dashboard with:")
    print("\n  streamlit run src/frontend/admin_dashboard.py")
    
    print("\nRun the analytics dashboard with:")
    print("\n  streamlit run src/frontend/analytics_dashboard.py")
    
    print("\nOr integrate into your main Streamlit app:")
    print("""
    import streamlit as st
    from src.frontend.admin_dashboard import render_admin_dashboard
    from src.frontend.analytics_dashboard import render_analytics_dashboard
    
    # In your main app
    if is_admin(user):
        if st.sidebar.checkbox("Admin Dashboard"):
            render_admin_dashboard(token, username)
    
        if st.sidebar.checkbox("Analytics"):
            render_analytics_dashboard()
    """)
    
    return True


async def create_admin_user():
    """Guide for creating admin user."""
    print_header("Creating Admin User")
    
    print("Create an admin user in your database with:")
    print("""
    # In your database client
    INSERT INTO users (username, email, password_hash, is_admin, is_active)
    VALUES ('admin', 'admin@example.com', <hashed_password>, true, true)
    
    # Then generate admin token:
    from src.tools.security_utils import TokenManager
    
    token = TokenManager.create_admin_token(
        user_id=1,
        username="admin"
    )
    print(f"Admin token: {token}")
    """)
    
    return True


async def test_endpoints():
    """Guide for testing API endpoints."""
    print_header("Testing API Endpoints")
    
    print("After starting your FastAPI server, test endpoints:\n")
    
    print("1. Get Dashboard Stats:")
    print("   curl -H 'Authorization: Bearer <token>' http://localhost:8000/admin/dashboard/stats")
    
    print("\n2. Get All Users:")
    print("   curl -H 'Authorization: Bearer <token>' http://localhost:8000/admin/users")
    
    print("\n3. Get User Analytics:")
    print("   curl -H 'Authorization: Bearer <token>' http://localhost:8000/analytics/user")
    
    print("\n4. Get Performance Analysis:")
    print("   curl -H 'Authorization: Bearer <token>' http://localhost:8000/analytics/performance")
    
    print("\nOr use Python:")
    print("""
    import requests
    
    token = "<your-admin-token>"
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test admin stats
    response = requests.get(
        "http://localhost:8000/admin/dashboard/stats",
        headers=headers
    )
    print(response.json())
    """)
    
    return True


async def verify_analytics_engine():
    """Verify analytics engine works."""
    print_header("Testing Analytics Engine")
    
    print("Test the analytics engine directly:\n")
    
    print("Python code:")
    print("""
    from src.analytics.advanced_analytics import AnalyticsEngine
    from datetime import datetime, timedelta
    
    engine = AnalyticsEngine()
    
    # Test trend detection
    data_points = [
        (datetime.now() - timedelta(days=i), 70 + i)
        for i in range(10)
    ]
    trend = engine.detect_trend(data_points)
    print(f"Trend: {trend.direction}, Strength: {trend.strength}")
    
    # Test anomaly detection
    scores = [75, 78, 76, 80, 150]  # 150 is anomaly
    anomalies = engine.detect_anomalies(scores)
    print(f"Anomalies found: {anomalies}")
    
    # Test statistics
    stats = engine.calculate_statistics(scores)
    print(f"Statistics: {stats}")
    """)
    
    return True


async def setup_monitoring():
    """Set up monitoring and logging."""
    print_header("Setting Up Monitoring & Logging")
    
    print("Configure logging in your application:\n")
    
    print("src/config.py:")
    print("""
    import logging
    from logging.handlers import RotatingFileHandler
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Add file handler
    handler = RotatingFileHandler(
        'logs/admin_activity.log',
        maxBytes=10485760,  # 10MB
        backupCount=10
    )
    logging.getLogger('admin').addHandler(handler)
    """)
    
    print("\nMonitor these logs:")
    print("  - Admin actions: logs/admin_activity.log")
    print("  - Security events: logs/security.log")
    print("  - API errors: logs/api_errors.log")
    
    return True


async def performance_optimization():
    """Performance optimization tips."""
    print_header("Performance Optimization")
    
    print("Optimize your Phase 6 deployment:\n")
    
    print("1. Database Optimization:")
    print("   - Create indexes on frequently queried columns")
    print("   - Index user_id, timestamp, action columns")
    print("   - Use query caching for expensive aggregations")
    
    print("\n2. Cache Strategy:")
    print("   - Cache dashboard stats (5-minute TTL)")
    print("   - Cache user activity summaries")
    print("   - Use Redis for session storage")
    
    print("\n3. API Optimization:")
    print("   - Implement pagination for all list endpoints")
    print("   - Use database-level filtering")
    print("   - Compress JSON responses")
    
    print("\n4. Frontend Optimization:")
    print("   - Cache Streamlit components")
    print("   - Use st.cache_data for expensive calculations")
    print("   - Implement virtual scrolling for large lists")
    
    return True


async def security_checklist():
    """Security checklist."""
    print_header("Security Checklist")
    
    checklist = [
        ("Change SECRET_KEY from default", False),
        ("Enable HTTPS for API", False),
        ("Configure database encryption", False),
        ("Set up MFA for admin accounts", False),
        ("Enable audit logging", False),
        ("Configure rate limiting", False),
        ("Set appropriate token expiration", False),
        ("Back up admin credentials securely", False),
        ("Regular security audits", False),
        ("Implement data retention policies", False)
    ]
    
    print("Complete these security items:\n")
    for item, done in checklist:
        status = "✓" if done else "○"
        print(f"  {status} {item}")
    
    return True


async def final_checklist():
    """Final implementation checklist."""
    print_header("Final Implementation Checklist")
    
    print("Complete these steps to fully deploy Phase 6:\n")
    
    steps = [
        "✓ Install phase6_requirements.txt packages",
        "○ Update SecurityConfig with production values",
        "○ Set up database tables and indexes",
        "○ Create admin user account",
        "○ Integrate API routes in main FastAPI app",
        "○ Add Streamlit dashboard pages",
        "○ Configure logging and monitoring",
        "○ Set up Redis for caching (optional)",
        "○ Test all API endpoints",
        "○ Test admin dashboard access",
        "○ Test analytics calculations",
        "○ Review security settings",
        "○ Set up automated backups for audit logs",
        "○ Configure email alerts for security events",
        "○ Document admin procedures",
        "○ Train admins on dashboard usage"
    ]
    
    print("\n".join(steps))
    
    return True


async def print_quick_start():
    """Print quick start guide."""
    print_header("Quick Start Guide")
    
    print("""
1. Install Dependencies:
   pip install -r phase6_requirements.txt

2. Configure Security:
   Edit src/tools/security_utils.py
   Update SECRET_KEY and database settings

3. Initialize Database:
   Run database migration for admin tables

4. Create Admin User:
   Use your database client or script

5. Start FastAPI Backend:
   python src/main.py

6. Start Admin Dashboard:
   streamlit run src/frontend/admin_dashboard.py

7. Generate Admin Token:
   Use TokenManager.create_admin_token()

8. Access Dashboard:
   Open http://localhost:8501
   Enter admin token when prompted

9. Monitor:
   Check logs in logs/ directory
   Review analytics on dashboard

For detailed documentation, see PHASE6_GUIDE.md
    """)


async def main():
    """Main setup flow."""
    print("\n" + "="*60)
    print("  Phase 6: Admin Dashboard & Analytics Setup")
    print("  Version: 1.0")
    print("  Updated: 2024")
    print("="*60)
    
    steps = [
        ("Verify Dependencies", verify_dependencies),
        ("Initialize Database", initialize_database),
        ("Configure Security", configure_security),
        ("Set Up API Routes", setup_api_routes),
        ("Set Up Streamlit", setup_streamlit),
        ("Create Admin User", create_admin_user),
        ("Test Endpoints", test_endpoints),
        ("Verify Analytics", verify_analytics_engine),
        ("Setup Monitoring", setup_monitoring),
        ("Optimize Performance", performance_optimization),
        ("Security Checklist", security_checklist),
        ("Final Checklist", final_checklist)
    ]
    
    for step_name, step_func in steps:
        try:
            await step_func()
        except Exception as e:
            print(f"Error in {step_name}: {e}")
            return 1
    
    await print_quick_start()
    
    print("\n✅ Phase 6 Setup Complete!")
    print("Next steps: Follow the Quick Start Guide above\n")
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
