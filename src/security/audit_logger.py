"""
Audit logging system for tracking queries and security events.
Follows SonarQube standards S4829 (logging), S6212 (sensitive data).
"""

import logging
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session as SQLSession

from src.database.models import AuditLog
from src.security.input_validator import InputValidator

logger = logging.getLogger(__name__)


class AuditLogger:
    """Logs all user queries and security events to database."""

    @staticmethod
    def log_query(
        db_session: SQLSession,
        user_id: int,
        query: str,
        subject: Optional[str] = None,
        tool_used: Optional[str] = None,
        response_length: int = 0,
        is_injection_flagged: bool = False,
        is_out_of_scope: bool = False,
        error_message: Optional[str] = None,
    ) -> bool:
        """
        Log a user query to the audit database.

        Args:
            db_session: Database session
            user_id: User ID
            query: User query text (will be sanitized)
            subject: IGCSE subject (optional)
            tool_used: Tool name (optional)
            response_length: Length of response
            is_injection_flagged: Whether injection was detected
            is_out_of_scope: Whether query was out of scope
            error_message: Any error message (optional)

        Returns:
            True if logged successfully, False otherwise
        """
        try:
            # Sanitize query for storage
            sanitized_query = InputValidator.sanitize_query(query)

            # Extract subject if not provided
            if not subject:
                subject = InputValidator.extract_subject(query)

            # Create audit log entry
            audit_log = AuditLog(
                user_id=user_id,
                query_text=sanitized_query,
                subject=subject,
                tool_used=tool_used,
                response_length=response_length,
                is_injection_flagged=is_injection_flagged,
                is_out_of_scope=is_out_of_scope,
                error_message=error_message[:500] if error_message else None,
                created_at=datetime.utcnow(),
            )

            db_session.add(audit_log)
            db_session.commit()

            logger.info(
                f"Query logged: user_id={user_id}, subject={subject}, "
                f"injection_flagged={is_injection_flagged}, out_of_scope={is_out_of_scope}"
            )

            return True

        except Exception as e:
            logger.error(f"Error logging query to database: {str(e)}")
            try:
                db_session.rollback()
            except Exception as rollback_error:
                logger.error(f"Error rolling back transaction: {str(rollback_error)}")
            return False

    @staticmethod
    def get_user_query_history(
        db_session: SQLSession,
        user_id: int,
        limit: int = 50,
    ) -> list:
        """
        Get user's query history.

        Args:
            db_session: Database session
            user_id: User ID
            limit: Maximum number of records to return

        Returns:
            List of AuditLog objects
        """
        try:
            logs = (
                db_session.query(AuditLog)
                .filter_by(user_id=user_id)
                .order_by(AuditLog.created_at.desc())
                .limit(limit)
                .all()
            )

            return logs

        except Exception as e:
            logger.error(f"Error retrieving query history: {str(e)}")
            return []

    @staticmethod
    def get_security_alerts(
        db_session: SQLSession,
        limit: int = 100,
    ) -> list:
        """
        Get recent security alerts (injection attempts, out-of-scope queries).

        Args:
            db_session: Database session
            limit: Maximum number of records to return

        Returns:
            List of AuditLog objects with security flags
        """
        try:
            alerts = (
                db_session.query(AuditLog)
                .filter(
                    (AuditLog.is_injection_flagged == True) |
                    (AuditLog.is_out_of_scope == True)
                )
                .order_by(AuditLog.created_at.desc())
                .limit(limit)
                .all()
            )

            return alerts

        except Exception as e:
            logger.error(f"Error retrieving security alerts: {str(e)}")
            return []

    @staticmethod
    def get_query_statistics(db_session: SQLSession) -> dict:
        """
        Get query statistics for admin dashboard.

        Args:
            db_session: Database session

        Returns:
            Dictionary with statistics
        """
        try:
            total_queries = db_session.query(AuditLog).count()
            injection_attempts = db_session.query(AuditLog).filter_by(
                is_injection_flagged=True
            ).count()
            out_of_scope_queries = db_session.query(AuditLog).filter_by(
                is_out_of_scope=True
            ).count()

            # Query by subject
            subject_stats = {}
            subjects = [
                "english",
                "maths",
                "science",
                "french",
                "finearts",
            ]
            for subject in subjects:
                count = db_session.query(AuditLog).filter_by(subject=subject).count()
                if count > 0:
                    subject_stats[subject] = count

            # Most used tools
            tool_stats = {}
            tools = [
                "french_tool",
                "igcse_tool",
                "quiz_tool",
            ]
            for tool in tools:
                count = db_session.query(AuditLog).filter_by(tool_used=tool).count()
                if count > 0:
                    tool_stats[tool] = count

            return {
                "total_queries": total_queries,
                "injection_attempts": injection_attempts,
                "out_of_scope_queries": out_of_scope_queries,
                "subject_distribution": subject_stats,
                "tool_usage": tool_stats,
                "security_threats_percentage": (
                    (injection_attempts + out_of_scope_queries) / total_queries * 100
                    if total_queries > 0
                    else 0
                ),
            }

        except Exception as e:
            logger.error(f"Error calculating query statistics: {str(e)}")
            return {
                "total_queries": 0,
                "injection_attempts": 0,
                "out_of_scope_queries": 0,
            }

    @staticmethod
    def cleanup_old_logs(db_session: SQLSession, days: int = 90) -> int:
        """
        Delete audit logs older than specified days.

        Args:
            db_session: Database session
            days: Age threshold in days

        Returns:
            Number of logs deleted
        """
        try:
            from datetime import timedelta

            cutoff_date = datetime.utcnow() - timedelta(days=days)

            logs_to_delete = db_session.query(AuditLog).filter(
                AuditLog.created_at < cutoff_date
            ).all()

            count = len(logs_to_delete)
            for log in logs_to_delete:
                db_session.delete(log)

            db_session.commit()

            logger.info(f"Deleted {count} audit logs older than {days} days")
            return count

        except Exception as e:
            db_session.rollback()
            logger.error(f"Error cleaning up audit logs: {str(e)}")
            return 0

    @staticmethod
    def log_security_event(
        db_session: SQLSession,
        user_id: int,
        event_type: str,
        details: str,
    ) -> bool:
        """
        Log a security event (login attempt, failed auth, etc.).

        Args:
            db_session: Database session
            user_id: User ID
            event_type: Type of event
            details: Event details

        Returns:
            True if logged successfully
        """
        try:
            # Use audit_logs table with special formatting
            query_text = f"[SECURITY EVENT] {event_type}: {details}"
            
            audit_log = AuditLog(
                user_id=user_id,
                query_text=query_text,
                subject="SECURITY",
                tool_used=None,
                response_length=0,
                is_injection_flagged=False,
                is_out_of_scope=False,
                created_at=datetime.utcnow(),
            )

            db_session.add(audit_log)
            db_session.commit()

            logger.warning(f"Security event logged: {event_type} for user_id={user_id}")
            return True

        except Exception as e:
            db_session.rollback()
            logger.error(f"Error logging security event: {str(e)}")
            return False
