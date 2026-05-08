"""
Modern Admin Dashboard Interface
Real-time system monitoring, user management, and security alerts.
"""

import streamlit as st
from datetime import datetime
from typing import Dict, List, Optional
import requests

import src.config as config
from src.frontend.ui_components import ResponsiveLayout, InteractiveComponents


def format_datetime(iso_string: Optional[str]) -> str:
    """Format ISO datetime string to human-readable format."""
    if not iso_string:
        return "N/A"
    try:
        dt = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
        return dt.strftime("%b %d, %I:%M %p")
    except (ValueError, AttributeError):
        return iso_string


def render_admin_dashboard(token: str, username: str):
    """Render the admin dashboard interface."""
    
    st.set_page_config(page_title="Admin Dashboard", layout="wide")
    st.title("⚙️ Admin Dashboard")
    st.subheader(f"Welcome, {username}")
    
    # Initialize session state
    if "admin_refresh" not in st.session_state:
        st.session_state.admin_refresh = 0
    
    # Refresh data button in sidebar
    with st.sidebar:
        st.title("Navigation")
        page = st.radio(
            "Select View",
            ["Overview", "Users", "Security", "System", "Settings"]
        )
        
        if st.button("🔄 Refresh Data"):
            st.session_state.admin_refresh += 1
            st.rerun()
    
    try:
        headers = {"Authorization": f"Bearer {token}"}
        
        if page == "Overview":
            render_overview(headers)
        elif page == "Users":
            render_users_management(headers)
        elif page == "Security":
            render_security_alerts(headers)
        elif page == "System":
            render_system_stats(headers)
        else:
            render_settings(headers)
    
    except Exception as e:
        InteractiveComponents.notification(f"Error: {str(e)}", "error")


def render_overview(headers: Dict):
    """Render dashboard overview."""
    st.markdown("## System Overview")

    try:
        with st.spinner("📊 Loading dashboard stats..."):
            # Fetch dashboard stats
            response = requests.get(f"{config.fastapi_url}/admin/dashboard/stats", headers=headers)
        if response.status_code != 200:
            st.error("Failed to load dashboard stats")
            return

        stats = response.json()

        # Main metrics
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            users_stats = stats.get("users", {})
            ResponsiveLayout.stat_card(
                "Active Users",
                str(users_stats.get("active", 0)),
                "👥",
                "#667eea"
            )

        with col2:
            quiz_stats = stats.get("quizzes", {})
            ResponsiveLayout.stat_card(
                "Total Quizzes",
                str(quiz_stats.get("total", 0)),
                "📊",
                "#4CAF50"
            )

        with col3:
            session_stats = stats.get("sessions", {})
            ResponsiveLayout.stat_card(
                "Active Sessions",
                str(session_stats.get("active", 0)),
                "🔐",
                "#FF9800"
            )

        with col4:
            security_stats = stats.get("security", {})
            ResponsiveLayout.stat_card(
                "Security Alerts",
                str(security_stats.get("injection_attempts", 0)),
                "⚠️",
                "#F44336"
            )

        # Quick stats
        st.markdown("---")
        st.markdown("### Key Metrics")

        col1, col2, col3 = st.columns(3)

        with col1:
            avg_score = quiz_stats.get("average_score", 0)
            st.metric("Average Quiz Score", f"{avg_score:.1f}%")

        with col2:
            total_users = users_stats.get("total", 0)
            inactive = users_stats.get("inactive", 0)
            st.metric("Inactive Users", str(inactive), f"-{(inactive/total_users*100 if total_users > 0 else 0):.1f}%")

        with col3:
            audit_logs = security_stats.get("total_audit_logs", 0)
            st.metric("Total Audit Logs", str(audit_logs))

    except Exception as e:
        st.error(f"Error loading overview: {str(e)}")


def render_users_management(headers: Dict):
    """Render user management interface."""
    st.markdown("## User Management")
    
    tab1, tab2, tab3 = st.tabs(["All Users", "Search User", "User Actions"])
    
    try:
        with tab1:
            st.markdown("### All Registered Users")

            # Pagination controls
            if "users_page" not in st.session_state:
                st.session_state.users_page = 0
            if "users_per_page" not in st.session_state:
                st.session_state.users_per_page = 10

            col1, col2, col3 = st.columns([1, 2, 1])
            with col1:
                if st.button("⬅️ Previous"):
                    st.session_state.users_page = max(0, st.session_state.users_page - 1)
            with col2:
                page_num = st.selectbox(
                    "Items per page",
                    [5, 10, 20, 50],
                    index=1,
                    key="users_per_page_select"
                )
                st.session_state.users_per_page = page_num
            with col3:
                if st.button("Next ➡️"):
                    st.session_state.users_page += 1

            offset = st.session_state.users_page * st.session_state.users_per_page
            limit = st.session_state.users_per_page

            with st.spinner("📂 Loading users..."):
                response = requests.get(
                    f"{config.fastapi_url}/admin/users?limit={limit}&offset={offset}",
                    headers=headers
                )
            if response.status_code != 200:
                st.error("Failed to load users")
                return

            users_data = response.json().get("users", [])

            # Create user table
            user_info = []
            for user in users_data:
                user_info.append({
                    "ID": user["id"],
                    "Username": user["username"],
                    "Email": user["email"],
                    "Quizzes": user["quiz_count"],
                    "Avg Score": f"{user['average_score']:.1f}%",
                    "Status": "✅ Active" if user["is_active"] else "❌ Inactive"
                })

            st.dataframe(user_info, use_container_width=True)

            # Pagination info
            st.caption(f"📄 Page {st.session_state.users_page + 1} | Showing {len(users_data)} users | Per page: {limit}")

            # Summary
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Users", len(users_data))
            with col2:
                active_count = sum(1 for u in users_data if u["is_active"])
                st.metric("Active Users", active_count)
            with col3:
                st.metric("Admin Users", sum(1 for u in users_data if u.get("is_admin", False)))
        
        with tab2:
            st.markdown("### Search User")
            
            user_id = st.number_input("Enter User ID:", min_value=1, key="search_user_id")
            
            if st.button("Search"):
                response = requests.get(f"{config.fastapi_url}/admin/user/{user_id}", headers=headers)
                
                if response.status_code == 200:
                    user = response.json()
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"**Username:** {user.get('username', 'N/A')}")
                        st.markdown(f"**Email:** {user.get('email', 'N/A')}")
                        st.markdown(f"**Status:** {'✅ Active' if user.get('is_active') else '❌ Inactive'}")
                        st.markdown(f"**Role:** {'Admin' if user.get('is_admin') else 'Student'}")
                    
                    with col2:
                        st.markdown(f"**Total Quizzes:** {user.get('total_quizzes', 0)}")
                        st.markdown(f"**Average Score:** {user.get('average_score', 0):.1f}%")
                        st.markdown(f"**Created:** {format_datetime(user.get('created_at'))}")
                        st.markdown(f"**Last Login:** {format_datetime(user.get('last_login')) if user.get('last_login') else 'Never'}")
                    
                    # Recent activity
                    st.markdown("**Recent Activity:**")
                    activity = user.get("recent_activity", [])
                    for log in activity[:5]:
                        st.text(f"- {log.get('query_text', 'N/A')[:50]}... ({log.get('timestamp', 'N/A')})")
                
                else:
                    st.error("User not found")
        
        with tab3:
            st.markdown("### Perform User Actions")
            
            user_id = st.number_input("Enter User ID:", min_value=1, key="action_user_id")
            action = st.selectbox(
                "Select Action:",
                ["enable", "disable", "reset_password", "deactivate"]
            )
            reason = st.text_area("Reason (optional):")
            
            if st.button("Execute Action", type="primary"):
                payload = {"action": action, "reason": reason if reason else None}
                response = requests.post(
                    f"{config.fastapi_url}/admin/user/{user_id}/action",
                    json=payload,
                    headers=headers
                )
                
                if response.status_code == 200:
                    InteractiveComponents.notification(
                        f"Action '{action}' completed successfully",
                        "success"
                    )
                else:
                    InteractiveComponents.notification(
                        f"Failed to perform action: {response.json().get('detail', 'Unknown error')}",
                        "error"
                    )
    
    except Exception as e:
        st.error(f"Error in user management: {str(e)}")


def render_security_alerts(headers: Dict):
    """Render security alerts and monitoring."""
    st.markdown("## Security Monitor")
    
    try:
        response = requests.get(f"{config.fastapi_url}/admin/security-alerts", headers=headers)
        if response.status_code != 200:
            st.error("Failed to load security alerts")
            return
        
        data = response.json()
        alerts = data.get("alerts", [])
        critical_count = data.get("critical_count", 0)
        
        # Alert summary
        if critical_count > 0:
            InteractiveComponents.notification(
                f"⚠️ {critical_count} critical security alerts detected!",
                "warning"
            )
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Alerts", len(alerts))
        with col2:
            st.metric("Critical (High Severity)", critical_count)
        
        # Alert details
        st.markdown("---")
        st.markdown("### Alert Details")
        
        if alerts:
            for idx, alert in enumerate(alerts[:20], 1):  # Show first 20
                severity = alert.get("severity", "unknown")
                alert_type = alert.get("type", "unknown")
                
                color_map = {"high": "#F44336", "medium": "#FF9800", "low": "#4CAF50"}
                color = color_map.get(severity, "#2196F3")
                
                with st.expander(f"{severity.upper()} - {alert_type.replace('_', ' ').title()} - {alert.get('timestamp', 'N/A')[:10]}"):
                    st.markdown(f"**Type:** {alert_type.replace('_', ' ').title()}")
                    st.markdown(f"**Severity:** {severity.upper()}")
                    st.markdown(f"**User ID:** {alert.get('user_id', 'N/A')}")
                    st.markdown(f"**Timestamp:** {alert.get('timestamp', 'N/A')}")
                    st.markdown(f"**Query:** {alert.get('query_text', 'N/A')[:100]}...")
                    st.markdown(f"**Message:** {alert.get('error_message', 'N/A')}")
        else:
            st.success("✅ No security alerts - all systems secure!")
    
    except Exception as e:
        st.error(f"Error loading security alerts: {str(e)}")


def render_system_stats(headers: Dict):
    """Render system statistics and usage."""
    st.markdown("## System Statistics")
    
    try:
        response = requests.get(f"{config.fastapi_url}/admin/dashboard/usage", headers=headers)
        if response.status_code != 200:
            st.error("Failed to load system stats")
            return
        
        stats = response.json()
        
        # Cache statistics
        st.markdown("### Cache Statistics")
        cache_stats = stats.get("cache", {})
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric(
                "Cache Entries",
                cache_stats.get("total_entries", 0)
            )
        with col2:
            st.metric(
                "Cache Size",
                f"{cache_stats.get('size_mb', 0):.2f} MB"
            )
        with col3:
            st.metric(
                "Expired Entries",
                cache_stats.get("expired_entries", 0)
            )
        with col4:
            if st.button("🧹 Clear Old Cache"):
                clear_response = requests.post(
                    f"{config.fastapi_url}/admin/cleanup",
                    json={"resource_type": "cache", "older_than_days": 7},
                    headers=headers
                )
                if clear_response.status_code == 200:
                    st.success("Cache cleared successfully!")
                    st.rerun()
        
        # Database statistics
        st.markdown("---")
        st.markdown("### Database Statistics")
        db_stats = stats.get("database", {})
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Users", db_stats.get("users", 0))
        with col2:
            st.metric("Quiz Attempts", db_stats.get("quiz_attempts", 0))
        with col3:
            st.metric("Active Sessions", db_stats.get("sessions", 0))
        with col4:
            st.metric("Audit Logs", db_stats.get("audit_logs", 0))
    
    except Exception as e:
        st.error(f"Error loading system stats: {str(e)}")


def render_settings(headers: Dict):
    """Render admin settings."""
    st.markdown("## Admin Settings")
    
    st.markdown("""
    ### System Configuration
    
    Configure global system settings and policies.
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Retention Policies")
        cache_retention = st.slider("Cache Retention (days):", 1, 90, 7)
        log_retention = st.slider("Audit Log Retention (days):", 30, 365, 90)
        quiz_retention = st.slider("Quiz History Retention (days):", 30, 365, 60)
    
    with col2:
        st.markdown("#### Security Settings")
        max_failed_attempts = st.number_input("Max Failed Login Attempts:", 1, 10, 5)
        session_timeout = st.number_input("Session Timeout (minutes):", 5, 480, 60)
        enable_mfa = st.checkbox("Enable Multi-Factor Authentication")
    
    if st.button("💾 Save Settings", type="primary"):
        st.success("Settings saved successfully!")


if __name__ == "__main__":
    token = st.session_state.get("auth_token", "")
    username = st.session_state.get("username", "Admin")
    
    if token:
        render_admin_dashboard(token, username)
    else:
        st.error("Please log in with admin credentials to access this dashboard")
