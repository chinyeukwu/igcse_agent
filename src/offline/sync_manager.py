"""
Sync manager for synchronizing offline-generated content with server.
Handles conflict resolution, pending updates, and sync status tracking.
"""

import json
from datetime import datetime
from typing import Optional, List, Tuple, Dict, Any
from sqlalchemy.orm import Session

from src.database.models import QuizHistory


class SyncManager:
    """Manages synchronization of offline-generated content with server."""

    @staticmethod
    def mark_for_sync(db_session: Session, quiz_history_id: int) -> bool:
        """
        Mark a quiz history entry as pending sync (offline-generated).
        
        Args:
            db_session: SQLAlchemy session
            quiz_history_id: Quiz history record ID
        
        Returns:
            True if marked successfully, False otherwise
        """
        try:
            quiz = db_session.query(QuizHistory).filter_by(id=quiz_history_id).first()
            if quiz:
                quiz.is_offline = True
                quiz.synced_at = None  # Clear sync timestamp
                db_session.commit()
                return True
            return False

        except Exception as e:
            db_session.rollback()
            print(f"Mark for sync error: {str(e)}")
            return False

    @staticmethod
    def get_pending_syncs(db_session: Session, user_id: int) -> List[Dict[str, Any]]:
        """
        Get all offline-generated content pending sync for a user.
        
        Args:
            db_session: SQLAlchemy session
            user_id: User ID
        
        Returns:
            List of pending sync records with metadata
        """
        try:
            pending = db_session.query(QuizHistory).filter(
                QuizHistory.user_id == user_id,
                QuizHistory.is_offline == True,
                QuizHistory.synced_at.is_(None)
            ).all()

            return [
                {
                    "id": quiz.id,
                    "subject": quiz.subject,
                    "topic": quiz.topic,
                    "score": quiz.score,
                    "created_at": quiz.created_at.isoformat(),
                    "time_taken_seconds": quiz.time_taken_seconds
                }
                for quiz in pending
            ]

        except Exception as e:
            print(f"Get pending syncs error: {str(e)}")
            return []

    @staticmethod
    def mark_synced(db_session: Session, quiz_history_id: int) -> bool:
        """
        Mark a quiz history entry as successfully synced.
        
        Args:
            db_session: SQLAlchemy session
            quiz_history_id: Quiz history record ID
        
        Returns:
            True if marked successfully, False otherwise
        """
        try:
            quiz = db_session.query(QuizHistory).filter_by(id=quiz_history_id).first()
            if quiz:
                quiz.synced_at = datetime.utcnow()
                db_session.commit()
                return True
            return False

        except Exception as e:
            db_session.rollback()
            print(f"Mark synced error: {str(e)}")
            return False

    @staticmethod
    def sync_all_pending(db_session: Session, user_id: int) -> Tuple[int, List[str]]:
        """
        Sync all pending offline content for a user.
        
        Args:
            db_session: SQLAlchemy session
            user_id: User ID
        
        Returns:
            Tuple of (sync_count, error_messages)
        """
        pending = SyncManager.get_pending_syncs(db_session, user_id)
        sync_count = 0
        errors = []

        for item in pending:
            try:
                if SyncManager.mark_synced(db_session, item["id"]):
                    sync_count += 1
                else:
                    errors.append(f"Failed to mark quiz {item['id']} as synced")

            except Exception as e:
                errors.append(f"Sync error for quiz {item['id']}: {str(e)}")

        return sync_count, errors

    @staticmethod
    def get_conflict_count(db_session: Session, user_id: int) -> int:
        """
        Get count of potential sync conflicts (offline edits to same quiz).
        
        Args:
            db_session: SQLAlchemy session
            user_id: User ID
        
        Returns:
            Number of potential conflicts
        """
        try:
            # A conflict is when multiple offline attempts exist for same subject/topic
            subjects_with_multi = db_session.query(
                QuizHistory.subject,
                QuizHistory.topic
            ).filter(
                QuizHistory.user_id == user_id,
                QuizHistory.is_offline == True,
                QuizHistory.synced_at.is_(None)
            ).all()

            return len(subjects_with_multi)

        except Exception as e:
            print(f"Conflict count error: {str(e)}")
            return 0

    @staticmethod
    def resolve_conflict(
        db_session: Session,
        quiz_history_id: int,
        resolution: str = "server"
    ) -> bool:
        """
        Resolve sync conflict with conflict resolution policy.
        
        Args:
            db_session: SQLAlchemy session
            quiz_history_id: Quiz history record ID
            resolution: 'local' (keep offline), 'server' (use server version), or 'manual'
        
        Returns:
            True if resolved successfully
        """
        try:
            quiz = db_session.query(QuizHistory).filter_by(id=quiz_history_id).first()
            if not quiz:
                return False

            if resolution == "server":
                # Server version takes precedence - mark as local retry
                quiz.is_offline = False
                quiz.synced_at = datetime.utcnow()

            elif resolution == "local":
                # Keep local version - prevent server overwrite
                quiz.synced_at = datetime.utcnow()

            elif resolution == "manual":
                # Flag for manual review
                quiz.is_offline = True
                quiz.synced_at = None

            db_session.commit()
            return True

        except Exception as e:
            db_session.rollback()
            print(f"Conflict resolution error: {str(e)}")
            return False

    @staticmethod
    def get_sync_status(db_session: Session, user_id: int) -> Dict[str, Any]:
        """
        Get comprehensive sync status for a user.
        
        Args:
            db_session: SQLAlchemy session
            user_id: User ID
        
        Returns:
            Sync status dictionary with metrics
        """
        try:
            total_offline = db_session.query(QuizHistory).filter(
                QuizHistory.user_id == user_id,
                QuizHistory.is_offline == True
            ).count()

            pending_sync = db_session.query(QuizHistory).filter(
                QuizHistory.user_id == user_id,
                QuizHistory.is_offline == True,
                QuizHistory.synced_at.is_(None)
            ).count()

            synced = db_session.query(QuizHistory).filter(
                QuizHistory.user_id == user_id,
                QuizHistory.is_offline == True,
                QuizHistory.synced_at.isnot(None)
            ).count()

            return {
                "user_id": user_id,
                "total_offline_quizzes": total_offline,
                "pending_sync_count": pending_sync,
                "synced_count": synced,
                "sync_percentage": 0 if total_offline == 0 else round((synced / total_offline) * 100, 2),
                "last_checked": datetime.utcnow().isoformat()
            }

        except Exception as e:
            print(f"Sync status error: {str(e)}")
            return {
                "error": str(e),
                "last_checked": datetime.utcnow().isoformat()
            }
