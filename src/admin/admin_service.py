"""
Admin Service Module
Handles user management, query monitoring, system statistics, and admin actions.
"""

import json
import csv
from datetime import datetime, timedelta
from io import StringIO
from typing import List, Dict, Any, Tuple

from sqlalchemy import func
from sqlalchemy.orm import joinedload

from src.database import get_session
from src.database.models import User, AuditLog, QuizHistory, Session, OfflineCache, AdminSettings


class AdminService:
    """Admin service for managing users, monitizing queries, and system analytics."""
    
    # Role constants
    ADMIN_ROLE = "admin"
    USER_ROLE = "user"
    
    # Admin actions
    ACTION_ENABLE = "enable"
    ACTION_DISABLE = "disable"
    ACTION_RESET_PASSWORD = "reset_password"
    ACTION_DEACTIVATE = "deactivate"
    
    @staticmethod
    def verify_admin_access(user_id: int, db_session) -> Tuple[bool, str]:
        """
        Verify if user has admin access.
        
        Args:
            user_id: User ID to check
            db_session: Database session
            
        Returns:
            (is_admin, error_message)
        """
        try:
            if not user_id:
                return False, "User ID required"
            
            user = db_session.query(User).filter(User.id == user_id).first()
            if not user:
                return False, "User not found"
            
            # Check admin role from settings
            admin_setting = db_session.query(AdminSettings).filter(
                AdminSettings.setting_key == f"admin_role_{user_id}"
            ).first()
            
            if admin_setting and admin_setting.setting_value == "true":
                return True, ""
            
            return False, "User does not have admin access"
        
        except Exception as e:
            return False, f"Admin verification error: {str(e)}"
    
    @staticmethod
    def get_all_users(db_session, limit: int = 100, offset: int = 0) -> Tuple[bool, List[Dict], str]:
        """
        Get all users with statistics.

        Args:
            db_session: Database session
            limit: Max records to return
            offset: Record offset for pagination

        Returns:
            (success, users_list, error_message)
        """
        try:
            # Subquery to get quiz stats per user
            quiz_stats = db_session.query(
                QuizHistory.user_id,
                func.count(QuizHistory.id).label("quiz_count"),
                func.avg(QuizHistory.score).label("avg_score")
            ).group_by(QuizHistory.user_id).subquery()

            # Subquery to get active session count per user
            active_session_stats = db_session.query(
                Session.user_id,
                func.count(Session.id).label("active_sessions")
            ).filter(
                Session.expires_at > datetime.utcnow()
            ).group_by(Session.user_id).subquery()

            # Get base users with pagination
            users = db_session.query(User).limit(limit).offset(offset).all()

            # Fetch admin settings and build lookup for efficiency
            admin_settings = db_session.query(AdminSettings).filter(
                AdminSettings.setting_key.like("admin_role_%")
            ).all()
            admin_dict = {
                int(s.setting_key.split("_")[-1]): s.setting_value == "true"
                for s in admin_settings if s.setting_key.startswith("admin_role_")
            }

            # Fetch quiz and session stats in bulk
            quiz_data = db_session.query(quiz_stats).all()
            quiz_dict = {row[0]: (row[1], row[2]) for row in quiz_data}

            session_data = db_session.query(active_session_stats).all()
            session_dict = {row[0]: row[1] for row in session_data}

            # Build result using cached lookups
            users_list = []
            for user in users:
                quiz_count, avg_score_val = quiz_dict.get(user.id, (0, 0.0))
                avg_score = float(avg_score_val) if avg_score_val else 0.0
                active_sessions = session_dict.get(user.id, 0)

                users_list.append({
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "full_name": user.full_name,
                    "is_active": user.is_active,
                    "is_admin": admin_dict.get(user.id, False),
                    "created_at": user.created_at.isoformat() if user.created_at else None,
                    "last_login": user.last_login.isoformat() if user.last_login else None,
                    "quiz_count": quiz_count,
                    "average_score": round(avg_score, 2),
                    "active_sessions": active_sessions
                })

            return True, users_list, ""

        except Exception as e:
            return False, [], f"Error fetching users: {str(e)}"
    
    @staticmethod
    def get_user_detail(db_session, user_id: int) -> Tuple[bool, Dict, str]:
        """
        Get detailed user information with activity history.
        
        Args:
            db_session: Database session
            user_id: User ID
            
        Returns:
            (success, user_detail, error_message)
        """
        try:
            user = db_session.query(User).filter(User.id == user_id).first()
            if not user:
                return False, {}, "User not found"
            
            # Get user activity - query fresh data without lazy loading
            activity_logs = db_session.query(AuditLog).filter(
                AuditLog.user_id == user_id
            ).order_by(AuditLog.created_at.desc()).limit(20).all()
            
            activity_data = []
            for log in activity_logs:
                activity_data.append({
                    "query_text": log.query_text[:100] + "..." if len(log.query_text or "") > 100 else log.query_text,
                    "subject": log.subject,
                    "timestamp": log.created_at.isoformat() if log.created_at else None,
                    "injection_flagged": log.is_injection_flagged,
                    "out_of_scope": log.is_out_of_scope
                })
            
            # Get quiz history
            quizzes = db_session.query(QuizHistory).filter(
                QuizHistory.user_id == user_id
            ).order_by(QuizHistory.created_at.desc()).limit(10).all()
            
            quiz_history = []
            for q in quizzes:
                quiz_history.append({
                    "id": q.id,
                    "subject": q.subject,
                    "difficulty": q.difficulty,
                    "score": float(q.score or 0),
                    "created_at": q.created_at.isoformat() if q.created_at else None
                })
            
            # Check admin status
            admin_setting = db_session.query(AdminSettings).filter(
                AdminSettings.setting_key == f"admin_role_{user_id}"
            ).first()
            is_admin = admin_setting and admin_setting.setting_value == "true"
            
            user_detail = {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name or "Not provided",
                "is_active": user.is_active,
                "is_admin": is_admin,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "last_login": user.last_login.isoformat() if user.last_login else "Never",
                "total_quizzes": len(quizzes),
                "average_score": round(sum([float(q.score or 0) for q in quizzes]) / len(quizzes), 2) if quizzes else 0,
                "activity_count": len(activity_data),
                "recent_activity": activity_data,
                "recent_quizzes": quiz_history
            }
            
            return True, user_detail, ""
        
        except Exception as e:
            return False, {}, f"Error fetching user detail: {str(e)}"
    
    @staticmethod
    def perform_user_action(db_session, user_id: int, action: str) -> Tuple[bool, str]:
        """
        Perform admin action on user (enable, disable, reset password, deactivate).
        
        Args:
            db_session: Database session
            user_id: User ID
            action: Action to perform (enable, disable, reset_password, deactivate)
            
        Returns:
            (success, message)
        """
        try:
            user = db_session.query(User).filter(User.id == user_id).first()
            if not user:
                return False, "User not found"
            
            if action == AdminService.ACTION_ENABLE:
                user.is_active = True
                db_session.commit()
                return True, f"User {user.username} enabled"
            
            elif action == AdminService.ACTION_DISABLE:
                user.is_active = False
                db_session.commit()
                return True, f"User {user.username} disabled"
            
            elif action == AdminService.ACTION_DEACTIVATE:
                user.is_active = False
                # Invalidate all sessions
                db_session.query(Session).filter(
                    Session.user_id == user_id
                ).delete()
                db_session.commit()
                return True, f"User {user.username} deactivated and all sessions terminated"
            
            elif action == AdminService.ACTION_RESET_PASSWORD:
                # Don't actually reset - just log the action
                return True, f"Password reset requested for user {user.username}"
            
            else:
                return False, f"Unknown action: {action}"
        
        except Exception as e:
            return False, f"Error performing user action: {str(e)}"
    
    @staticmethod
    def get_monitored_queries(
        db_session,
        user_id: int = None,
        subject: str = None,
        start_date: str = None,
        end_date: str = None,
        has_injection_flag: bool = None,
        limit: int = 100
    ) -> Tuple[bool, List[Dict], str]:
        """
        Get monitored queries with filtering options.
        
        Args:
            db_session: Database session
            user_id: Filter by user (optional)
            subject: Filter by subject (optional)
            start_date: Filter by start date ISO format (optional)
            end_date: Filter by end date ISO format (optional)
            has_injection_flag: Filter by injection detection (optional)
            limit: Max records
            
        Returns:
            (success, queries_list, error_message)
        """
        try:
            query = db_session.query(AuditLog)
            
            if user_id:
                query = query.filter(AuditLog.user_id == user_id)
            
            if subject:
                query = query.filter(AuditLog.subject == subject)
            
            if start_date:
                start_dt = datetime.fromisoformat(start_date)
                query = query.filter(AuditLog.created_at >= start_dt)
            
            if end_date:
                end_dt = datetime.fromisoformat(end_date)
                query = query.filter(AuditLog.created_at <= end_dt)
            
            if has_injection_flag is not None:
                query = query.filter(AuditLog.is_injection_flagged == has_injection_flag)
            
            logs = query.order_by(AuditLog.created_at.desc()).limit(limit).all()
            
            queries_list = []
            for log in logs:
                queries_list.append({
                    "id": log.id,
                    "user_id": log.user_id,
                    "query_text": log.query_text[:100] + "..." if len(log.query_text or "") > 100 else log.query_text,
                    "subject": log.subject,
                    "tool_used": log.tool_used,
                    "timestamp": log.created_at.isoformat() if log.created_at else None,
                    "injection_flagged": log.is_injection_flagged,
                    "out_of_scope": log.is_out_of_scope,
                    "error_message": log.error_message
                })
            
            return True, queries_list, ""
        
        except Exception as e:
            return False, [], f"Error fetching queries: {str(e)}"
    
    @staticmethod
    def get_security_alerts(db_session, limit: int = 50) -> Tuple[bool, List[Dict], str]:
        """
        Get security alerts including injection attempts and scope violations.
        
        Args:
            db_session: Database session
            limit: Max alerts to return
            
        Returns:
            (success, alerts_list, error_message)
        """
        try:
            # Get injection attempts
            injection_logs = db_session.query(AuditLog).filter(
                AuditLog.is_injection_flagged == True
            ).order_by(AuditLog.created_at.desc()).limit(limit).all()
            
            # Get scope violations
            violation_logs = db_session.query(AuditLog).filter(
                AuditLog.is_out_of_scope == True
            ).order_by(AuditLog.created_at.desc()).limit(limit).all()
            
            alerts = []
            
            # Add injection alerts
            for log in injection_logs:
                alerts.append({
                    "type": "injection_attempt",
                    "severity": "high",
                    "user_id": log.user_id,
                    "timestamp": log.created_at.isoformat() if log.created_at else None,
                    "subject": log.subject,
                    "query_text": log.query_text[:100] + "..." if len(log.query_text or "") > 100 else log.query_text,
                    "error_message": log.error_message
                })
            
            # Add violation alerts
            for log in violation_logs:
                alerts.append({
                    "type": "scope_violation",
                    "severity": "medium",
                    "user_id": log.user_id,
                    "timestamp": log.created_at.isoformat() if log.created_at else None,
                    "subject": log.subject,
                    "query_text": log.query_text[:100] + "..." if len(log.query_text or "") > 100 else log.query_text,
                    "error_message": log.error_message
                })
            
            # Sort by timestamp, most recent first
            alerts.sort(key=lambda x: x["timestamp"], reverse=True)
            
            return True, alerts[:limit], ""
        
        except Exception as e:
            return False, [], f"Error fetching security alerts: {str(e)}"
    
    @staticmethod
    def get_dashboard_statistics(db_session) -> Tuple[bool, Dict, str]:
        """
        Get overall system statistics for dashboard.
        
        Args:
            db_session: Database session
            
        Returns:
            (success, stats_dict, error_message)
        """
        try:
            # User statistics
            total_users = db_session.query(User).count()
            active_users = db_session.query(User).filter(User.is_active == True).count()
            
            # Quiz statistics
            total_quizzes = db_session.query(QuizHistory).count()
            
            avg_quiz_score = 0.0
            quiz_all = db_session.query(QuizHistory).all()
            if quiz_all:
                avg_quiz_score = sum([float(q.score or 0) for q in quiz_all]) / len(quiz_all)
            
            # Session statistics
            active_sessions = db_session.query(Session).filter(
                Session.expires_at > datetime.utcnow()
            ).count()
            
            # Security statistics
            injection_attempts = db_session.query(AuditLog).filter(
                AuditLog.is_injection_flagged == True
            ).count()
            
            total_audit_logs = db_session.query(AuditLog).count()
            
            stats = {
                "users": {
                    "total": total_users,
                    "active": active_users,
                    "inactive": total_users - active_users
                },
                "quizzes": {
                    "total": total_quizzes,
                    "average_score": round(avg_quiz_score, 2)
                },
                "sessions": {
                    "active": active_sessions
                },
                "security": {
                    "injection_attempts": injection_attempts,
                    "total_audit_logs": total_audit_logs
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
            return True, stats, ""
        
        except Exception as e:
            return False, {}, f"Error fetching dashboard statistics: {str(e)}"
    
    @staticmethod
    def get_usage_statistics(db_session) -> Tuple[bool, Dict, str]:
        """
        Get system usage statistics (storage, cache, database).
        
        Args:
            db_session: Database session
            
        Returns:
            (success, usage_dict, error_message)
        """
        try:
            # Cache statistics
            total_cache_entries = db_session.query(OfflineCache).count()
            
            cache_size_estimate = 0
            cache_entries = db_session.query(OfflineCache).all()
            for entry in cache_entries:
                if entry.response_json:
                    cache_size_estimate += len(entry.response_json)
            
            # Database statistics
            total_users = db_session.query(User).count()
            total_audit_logs = db_session.query(AuditLog).count()
            total_quizzes = db_session.query(QuizHistory).count()
            total_sessions = db_session.query(Session).count()
            
            # Expired cache entries
            expired_cache = db_session.query(OfflineCache).filter(
                OfflineCache.expires_at < datetime.utcnow()
            ).count()
            
            usage = {
                "cache": {
                    "total_entries": total_cache_entries,
                    "size_bytes": cache_size_estimate,
                    "size_mb": round(cache_size_estimate / (1024 * 1024), 2),
                    "expired_entries": expired_cache
                },
                "database": {
                    "users": total_users,
                    "audit_logs": total_audit_logs,
                    "quiz_attempts": total_quizzes,
                    "sessions": total_sessions
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
            return True, usage, ""
        
        except Exception as e:
            return False, {}, f"Error fetching usage statistics: {str(e)}"
    
    @staticmethod
    def cleanup_cache(db_session, older_than_days: int = 7) -> Tuple[bool, Dict, str]:
        """
        Clean up old cache entries.
        
        Args:
            db_session: Database session
            older_than_days: Delete entries older than this many days
            
        Returns:
            (success, cleanup_stats, error_message)
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=older_than_days)
            
            entries_to_delete = db_session.query(OfflineCache).filter(
                OfflineCache.created_at < cutoff_date
            ).all()
            
            deleted_count = len(entries_to_delete)
            freed_bytes = sum([len(e.response_json or "") for e in entries_to_delete])
            
            # Delete entries
            for entry in entries_to_delete:
                db_session.delete(entry)
            
            db_session.commit()
            
            return True, {
                "deleted_entries": deleted_count,
                "freed_bytes": freed_bytes,
                "freed_mb": round(freed_bytes / (1024 * 1024), 2),
                "cutoff_date": cutoff_date.isoformat()
            }, ""
        
        except Exception as e:
            return False, {}, f"Error cleaning up cache: {str(e)}"
    
    @staticmethod
    def cleanup_audit_logs(db_session, older_than_days: int = 90) -> Tuple[bool, Dict, str]:
        """
        Clean up old audit logs.
        
        Args:
            db_session: Database session
            older_than_days: Delete logs older than this many days
            
        Returns:
            (success, cleanup_stats, error_message)
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=older_than_days)
            
            count_result = db_session.query(AuditLog).filter(
                AuditLog.created_at < cutoff_date
            ).count()
            
            deleted_count = db_session.query(AuditLog).filter(
                AuditLog.created_at < cutoff_date
            ).delete()
            
            db_session.commit()
            
            return True, {
                "deleted_logs": deleted_count,
                "cutoff_date": cutoff_date.isoformat()
            }, ""
        
        except Exception as e:
            return False, {}, f"Error cleaning up audit logs: {str(e)}"
    
    @staticmethod
    def export_user_data(db_session, user_id: int, format: str = "json") -> Tuple[bool, str, str]:
        """
        Export user data for compliance (GDPR, etc).
        
        Args:
            db_session: Database session
            user_id: User ID to export
            format: Export format (json or csv)
            
        Returns:
            (success, data_export, error_message)
        """
        try:
            user = db_session.query(User).filter(User.id == user_id).first()
            if not user:
                return False, "", "User not found"
            
            # Gather user data
            user_info = {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "created_at": user.created_at.isoformat() if user.created_at else None
            }
            
            # Get user's quiz history
            quizzes = db_session.query(QuizHistory).filter(
                QuizHistory.user_id == user_id
            ).all()
            
            quiz_data = []
            for q in quizzes:
                quiz_data.append({
                    "id": q.id,
                    "subject": q.subject,
                    "difficulty": q.difficulty,
                    "score": float(q.score or 0),
                    "created_at": q.created_at.isoformat() if q.created_at else None
                })
            
            # Get user's audit logs
            logs = db_session.query(AuditLog).filter(
                AuditLog.user_id == user_id
            ).all()
            
            log_data = []
            for log in logs:
                log_data.append({
                    "action": log.action,
                    "status": log.status,
                    "timestamp": log.timestamp.isoformat() if log.timestamp else None
                })
            
            if format == "json":
                export_data = json.dumps({
                    "user": user_info,
                    "quizzes": quiz_data,
                    "audit_logs": log_data
                }, indent=2)
                return True, export_data, ""
            
            elif format == "csv":
                # Create CSV with multiple sheets represented as sections
                output = StringIO()
                
                # User info section
                output.write("USER_INFO\n")
                for key, value in user_info.items():
                    output.write(f"{key},{value}\n")
                
                output.write("\nQUIZ_HISTORY\n")
                output.write("id,subject,difficulty,score,created_at\n")
                for q in quiz_data:
                    output.write(f"{q['id']},{q['subject']},{q['difficulty']},{q['score']},{q['created_at']}\n")
                
                output.write("\nAUDIT_LOGS\n")
                output.write("action,status,timestamp\n")
                for log in log_data:
                    output.write(f"{log['action']},{log['status']},{log['timestamp']}\n")
                
                return True, output.getvalue(), ""
            
            else:
                return False, "", f"Unsupported format: {format}"
        
        except Exception as e:
            return False, "", f"Error exporting user data: {str(e)}"
