"""
Chat service for managing conversation history persistence.
Handles saving and loading chat messages from the database.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from src.database.models import ChatHistory

logger = logging.getLogger(__name__)


class ChatService:
    """Service for managing chat history persistence."""

    @staticmethod
    def save_message(
        db_session: Session,
        user_id: int,
        session_id: str,
        role: str,
        message: str
    ) -> bool:
        """
        Save a chat message to the database.

        Args:
            db_session: Database session
            user_id: User ID
            session_id: Chat session ID
            role: Message role (user|assistant)
            message: Message content

        Returns:
            True if saved successfully, False otherwise
        """
        try:
            chat_msg = ChatHistory(
                user_id=user_id,
                session_id=session_id,
                role=role,
                message=message,
                created_at=datetime.utcnow()
            )
            db_session.add(chat_msg)
            db_session.commit()
            logger.debug(f"Saved {role} message for user {user_id} in session {session_id}")
            return True
        except Exception as e:
            db_session.rollback()
            logger.error(f"Error saving chat message: {e}")
            return False

    @staticmethod
    def get_session_history(
        db_session: Session,
        user_id: int,
        session_id: str
    ) -> List[Dict[str, str]]:
        """
        Retrieve chat history for a specific session.

        Args:
            db_session: Database session
            user_id: User ID
            session_id: Chat session ID

        Returns:
            List of chat messages in format [{"role": "...", "message": "..."}, ...]
        """
        try:
            messages = db_session.query(ChatHistory).filter(
                ChatHistory.user_id == user_id,
                ChatHistory.session_id == session_id
            ).order_by(ChatHistory.created_at).all()

            return [
                {"role": msg.role, "message": msg.message}
                for msg in messages
            ]
        except Exception as e:
            logger.error(f"Error retrieving chat history: {e}")
            return []

    @staticmethod
    def get_latest_session(
        db_session: Session,
        user_id: int
    ) -> Optional[str]:
        """
        Get the most recent chat session ID for a user.

        Args:
            db_session: Database session
            user_id: User ID

        Returns:
            Session ID or None if no sessions exist
        """
        try:
            latest = db_session.query(ChatHistory).filter(
                ChatHistory.user_id == user_id
            ).order_by(ChatHistory.created_at.desc()).first()

            return latest.session_id if latest else None
        except Exception as e:
            logger.error(f"Error getting latest session: {e}")
            return None

    @staticmethod
    def clear_session(
        db_session: Session,
        user_id: int,
        session_id: str
    ) -> bool:
        """
        Delete all messages from a chat session.

        Args:
            db_session: Database session
            user_id: User ID
            session_id: Chat session ID

        Returns:
            True if cleared successfully, False otherwise
        """
        try:
            db_session.query(ChatHistory).filter(
                ChatHistory.user_id == user_id,
                ChatHistory.session_id == session_id
            ).delete()
            db_session.commit()
            logger.debug(f"Cleared chat session {session_id} for user {user_id}")
            return True
        except Exception as e:
            db_session.rollback()
            logger.error(f"Error clearing chat session: {e}")
            return False

    @staticmethod
    def delete_old_sessions(
        db_session: Session,
        user_id: int,
        days: int = 30
    ) -> int:
        """
        Delete chat sessions older than specified days.

        Args:
            db_session: Database session
            user_id: User ID
            days: Number of days to keep

        Returns:
            Number of messages deleted
        """
        try:
            from datetime import datetime, timedelta
            cutoff_date = datetime.utcnow() - timedelta(days=days)

            result = db_session.query(ChatHistory).filter(
                ChatHistory.user_id == user_id,
                ChatHistory.created_at < cutoff_date
            ).delete()
            db_session.commit()

            logger.debug(f"Deleted {result} old messages for user {user_id}")
            return result
        except Exception as e:
            db_session.rollback()
            logger.error(f"Error deleting old sessions: {e}")
            return 0
