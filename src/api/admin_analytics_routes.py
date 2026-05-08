"""
Admin and Analytics API Routes
Endpoints for admin dashboard, user management, and analytics.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthCredentials
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging

from src.models.agentstate import SessionState, User
from src.tools.security_utils import verify_admin_token, require_admin
from src.analytics.advanced_analytics import AnalyticsEngine

logger = logging.getLogger(__name__)

# Initialize routers
admin_router = APIRouter(prefix="/admin", tags=["admin"])
analytics_router = APIRouter(prefix="/analytics", tags=["analytics"])


# ==================== Admin Dashboard Routes ====================

@admin_router.get("/dashboard/stats")
async def get_dashboard_stats(
    credentials: HTTPAuthCredentials = Depends(HTTPBearer()),
    db = Depends()  # Database dependency
):
    """Get dashboard statistics for admin overview."""
    user = await require_admin(credentials.credentials, db)
    
    try:
        # Fetch statistics
        users_count = await db.count_users()
        active_users = await db.count_active_users()
        inactive_users = users_count - active_users
        
        quiz_attempts = await db.count_quiz_attempts()
        avg_score = await db.get_average_quiz_score()
        
        active_sessions = await db.count_active_sessions()
        
        # Security stats
        injection_attempts = await db.count_failed_auth_attempts(timedelta(days=1))
        total_audit_logs = await db.count_audit_logs()
        
        return {
            "users": {
                "total": users_count,
                "active": active_users,
                "inactive": inactive_users
            },
            "quizzes": {
                "total": quiz_attempts,
                "average_score": avg_score
            },
            "sessions": {
                "active": active_sessions
            },
            "security": {
                "injection_attempts": injection_attempts,
                "total_audit_logs": total_audit_logs
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error fetching dashboard stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch stats")


@admin_router.get("/users")
async def get_all_users(
    credentials: HTTPAuthCredentials = Depends(HTTPBearer()),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db = Depends()
):
    """Get all users with pagination."""
    user = await require_admin(credentials.credentials, db)
    
    try:
        users = await db.get_users_paginated(skip=skip, limit=limit)
        total = await db.count_users()
        
        users_data = []
        for u in users:
            quiz_stats = await db.get_user_quiz_stats(u.id)
            users_data.append({
                "id": u.id,
                "username": u.username,
                "email": u.email,
                "is_active": u.is_active,
                "is_admin": u.is_admin,
                "created_at": u.created_at.isoformat(),
                "last_login": u.last_login.isoformat() if u.last_login else None,
                "quiz_count": quiz_stats.get("count", 0),
                "average_score": quiz_stats.get("average_score", 0)
            })
        
        return {
            "users": users_data,
            "total": total,
            "skip": skip,
            "limit": limit
        }
    except Exception as e:
        logger.error(f"Error fetching users: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch users")


@admin_router.get("/user/{user_id}")
async def get_user_details(
    user_id: int,
    credentials: HTTPAuthCredentials = Depends(HTTPBearer()),
    db = Depends()
):
    """Get detailed user information."""
    admin = await require_admin(credentials.credentials, db)
    
    try:
        user = await db.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        quiz_stats = await db.get_user_quiz_stats(user_id)
        recent_activity = await db.get_user_activity(user_id, limit=10)
        
        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "is_active": user.is_active,
            "is_admin": user.is_admin,
            "created_at": user.created_at.isoformat(),
            "last_login": user.last_login.isoformat() if user.last_login else None,
            "total_quizzes": quiz_stats.get("count", 0),
            "average_score": quiz_stats.get("average_score", 0),
            "recent_activity": [
                {
                    "query_text": log.get("query_text", ""),
                    "timestamp": log.get("timestamp", "")
                }
                for log in recent_activity
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching user details: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch user details")


@admin_router.post("/user/{user_id}/action")
async def perform_user_action(
    user_id: int,
    action_data: Dict[str, Any],
    credentials: HTTPAuthCredentials = Depends(HTTPBearer()),
    db = Depends()
):
    """Perform administrative action on user."""
    admin = await require_admin(credentials.credentials, db)
    
    action = action_data.get("action")
    reason = action_data.get("reason")
    
    valid_actions = ["enable", "disable", "reset_password", "deactivate"]
    if action not in valid_actions:
        raise HTTPException(status_code=400, detail="Invalid action")
    
    try:
        user = await db.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        if action == "enable":
            user.is_active = True
        elif action == "disable":
            user.is_active = False
        elif action == "reset_password":
            await db.reset_user_password(user_id)
        elif action == "deactivate":
            user.is_active = False
        
        await db.update_user(user)
        
        # Log action
        await db.log_audit("user_action", {
            "admin_id": admin.id,
            "user_id": user_id,
            "action": action,
            "reason": reason
        })
        
        return {"status": "success", "message": f"Action '{action}' completed"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error performing user action: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to perform action")


@admin_router.get("/security-alerts")
async def get_security_alerts(
    credentials: HTTPAuthCredentials = Depends(HTTPBearer()),
    limit: int = Query(50, ge=1, le=500),
    db = Depends()
):
    """Get recent security alerts."""
    admin = await require_admin(credentials.credentials, db)
    
    try:
        alerts = await db.get_security_alerts(limit=limit)
        critical_count = sum(1 for a in alerts if a.get("severity") == "high")
        
        return {
            "alerts": alerts,
            "critical_count": critical_count,
            "total": len(alerts)
        }
    except Exception as e:
        logger.error(f"Error fetching security alerts: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch alerts")


@admin_router.get("/dashboard/usage")
async def get_system_usage(
    credentials: HTTPAuthCredentials = Depends(HTTPBearer()),
    db = Depends()
):
    """Get system usage statistics."""
    admin = await require_admin(credentials.credentials, db)
    
    try:
        cache_stats = await db.get_cache_stats()
        db_stats = await db.get_database_stats()
        
        return {
            "cache": cache_stats,
            "database": db_stats,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error fetching usage stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch stats")


@admin_router.post("/cleanup")
async def cleanup_resources(
    cleanup_data: Dict[str, Any],
    credentials: HTTPAuthCredentials = Depends(HTTPBearer()),
    background_tasks: BackgroundTasks,
    db = Depends()
):
    """Clean up old data and resources."""
    admin = await require_admin(credentials.credentials, db)
    
    resource_type = cleanup_data.get("resource_type")
    older_than_days = cleanup_data.get("older_than_days", 7)
    
    if resource_type not in ["cache", "logs", "sessions"]:
        raise HTTPException(status_code=400, detail="Invalid resource type")
    
    try:
        # Run cleanup in background
        background_tasks.add_task(
            db.cleanup_resources,
            resource_type=resource_type,
            older_than_days=older_than_days
        )
        
        # Log cleanup action
        await db.log_audit("cleanup", {
            "admin_id": admin.id,
            "resource_type": resource_type,
            "older_than_days": older_than_days
        })
        
        return {"status": "in_progress", "message": "Cleanup started"}
    except Exception as e:
        logger.error(f"Error initiating cleanup: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to initiate cleanup")


# ==================== Analytics Routes ====================

@analytics_router.get("/user")
async def get_user_analytics(
    credentials: HTTPAuthCredentials = Depends(HTTPBearer()),
    days: int = Query(30, ge=1, le=365),
    db = Depends()
):
    """Get user analytics for specified time period."""
    user = await require_admin(credentials.credentials, db)
    
    try:
        since_date = datetime.now() - timedelta(days=days)
        
        # Fetch quiz data
        quiz_attempts = await db.get_user_quiz_attempts(user.id, since_date=since_date)
        quiz_scores = [q.get("score", 0) for q in quiz_attempts]
        
        # Fetch activity log
        activity_log = await db.get_user_activity(user.id, limit=100)
        
        # Calculate metrics
        total_study_time = sum(q.get("duration_minutes", 0) for q in quiz_attempts)
        current_streak = await db.calculate_user_streak(user.id)
        
        return {
            "total_quizzes": len(quiz_attempts),
            "average_score": sum(quiz_scores) / len(quiz_scores) if quiz_scores else 0,
            "quiz_scores": quiz_scores,
            "total_study_time_minutes": total_study_time,
            "current_streak": current_streak,
            "activity_log": activity_log
        }
    except Exception as e:
        logger.error(f"Error fetching user analytics: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch analytics")


@analytics_router.get("/performance")
async def get_performance_analytics(
    credentials: HTTPAuthCredentials = Depends(HTTPBearer()),
    db = Depends()
):
    """Get performance analytics."""
    user = await require_admin(credentials.credentials, db)
    
    try:
        quiz_data = await db.get_user_quiz_data(user.id)
        
        quiz_scores = [q.get("score", 0) for q in quiz_data]
        quiz_times = [q.get("duration_minutes", 0) for q in quiz_data]
        
        return {
            "quiz_scores": quiz_scores,
            "quiz_times": quiz_times
        }
    except Exception as e:
        logger.error(f"Error fetching performance data: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch performance data")


@analytics_router.get("/learning-patterns")
async def get_learning_patterns(
    credentials: HTTPAuthCredentials = Depends(HTTPBearer()),
    db = Depends()
):
    """Get learning patterns."""
    user = await require_admin(credentials.credentials, db)
    
    try:
        activity_log = await db.get_user_activity(user.id, limit=1000)
        
        return {"activity_log": activity_log}
    except Exception as e:
        logger.error(f"Error fetching learning patterns: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch patterns")


@analytics_router.get("/user/quiz-scores")
async def get_quiz_scores(
    credentials: HTTPAuthCredentials = Depends(HTTPBearer()),
    db = Depends()
):
    """Get all quiz scores for user."""
    user = await require_admin(credentials.credentials, db)
    
    try:
        quiz_data = await db.get_user_quiz_data(user.id)
        scores = [q.get("score", 0) for q in quiz_data]
        
        return {"scores": scores}
    except Exception as e:
        logger.error(f"Error fetching quiz scores: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch scores")


@analytics_router.get("/insights")
async def get_user_insights(
    credentials: HTTPAuthCredentials = Depends(HTTPBearer()),
    db = Depends()
):
    """Get AI-generated insights for user."""
    user = await require_admin(credentials.credentials, db)
    
    try:
        engine = AnalyticsEngine()
        
        # Fetch data
        quiz_data = await db.get_user_quiz_data(user.id)
        activity_log = await db.get_user_activity(user.id, limit=100)
        
        # Generate insights
        insights = engine.generate_insights(
            quiz_data={"scores": [q.get("score", 0) for q in quiz_data]},
            user_profile={"id": user.id, "username": user.username},
            activity_log=activity_log
        )
        
        return {
            "insights": [
                {
                    "title": i.title,
                    "description": i.description,
                    "impact": i.impact,
                    "category": i.category,
                    "data_point": i.data_point,
                    "recommendation": i.recommendation
                }
                for i in insights
            ]
        }
    except Exception as e:
        logger.error(f"Error generating insights: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate insights")


# ==================== Advanced Analytics Routes ====================

@analytics_router.post("/export-report")
async def export_analytics_report(
    credentials: HTTPAuthCredentials = Depends(HTTPBearer()),
    report_data: Dict[str, Any] = None,
    db = Depends()
):
    """Export comprehensive analytics report."""
    user = await require_admin(credentials.credentials, db)
    
    try:
        engine = AnalyticsEngine()
        
        filename = f"/tmp/analytics_report_{user.id}_{datetime.now().timestamp()}.json"
        success = engine.export_analytics_report(filename, report_data or {})
        
        if success:
            return {
                "status": "success",
                "filename": filename,
                "message": "Report exported successfully"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to export report")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting report: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to export report")


@analytics_router.get("/trends")
async def get_trend_analysis(
    credentials: HTTPAuthCredentials = Depends(HTTPBearer()),
    metric: str = Query("quiz_scores"),
    window_size: int = Query(7, ge=2, le=30),
    db = Depends()
):
    """Get trend analysis for specified metric."""
    user = await require_admin(credentials.credentials, db)
    
    try:
        engine = AnalyticsEngine()
        
        # Fetch time-series data
        if metric == "quiz_scores":
            quiz_data = await db.get_user_quiz_data(user.id)
            data_points = [
                (datetime.fromisoformat(q.get("timestamp")), q.get("score", 0))
                for q in quiz_data
            ]
        else:
            raise HTTPException(status_code=400, detail="Invalid metric")
        
        trend = engine.detect_trend(data_points, window_size=window_size)
        
        return {
            "direction": trend.direction,
            "slope": trend.slope,
            "strength": trend.strength,
            "start_date": trend.start_date.isoformat(),
            "end_date": trend.end_date.isoformat(),
            "predicted_value": trend.predicted_value
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing trends: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to analyze trends")


@analytics_router.get("/anomalies")
async def detect_anomalies(
    credentials: HTTPAuthCredentials = Depends(HTTPBearer()),
    metric: str = Query("quiz_scores"),
    method: str = Query("zscore"),
    threshold: float = Query(2.0, ge=1.0, le=5.0),
    db = Depends()
):
    """Detect anomalies in data."""
    user = await require_admin(credentials.credentials, db)
    
    try:
        engine = AnalyticsEngine()
        
        # Fetch data
        if metric == "quiz_scores":
            quiz_data = await db.get_user_quiz_data(user.id)
            data_points = [q.get("score", 0) for q in quiz_data]
        else:
            raise HTTPException(status_code=400, detail="Invalid metric")
        
        anomalies = engine.detect_anomalies(data_points, method=method, threshold=threshold)
        
        return {
            "anomalies": [{"index": idx, "value": val} for idx, val in anomalies],
            "count": len(anomalies),
            "method": method
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error detecting anomalies: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to detect anomalies")


# Export routers for main app
def get_admin_routes():
    """Get admin router."""
    return admin_router


def get_analytics_routes():
    """Get analytics router."""
    return analytics_router
