"""
User service for authentication operations.
Handles user registration, login, logout, and profile management.
Follows SonarQube standards for security and data protection.
"""

import logging
from datetime import datetime
from typing import Optional, Tuple
from sqlalchemy.orm import Session as SQLSession
from sqlalchemy.exc import IntegrityError

from src.database.models import User, Session
from src.auth.password_utils import hash_password, verify_password, validate_password_strength
from src.auth.session_manager import SessionManager

logger = logging.getLogger(__name__)


class UserService:
    """Service for managing user authentication and profile operations."""

    @staticmethod
    def register_user(
        db_session: SQLSession,
        username: str,
        email: str,
        password: str,
        full_name: Optional[str] = None,
    ) -> Tuple[bool, Optional[str], Optional[User]]:
        """
        Register a new user.

        Args:
            db_session: Database session
            username: Unique username (3-50 chars)
            email: Valid email address
            password: Password (must meet security requirements)
            full_name: User's full name (optional)

        Returns:
            Tuple of (success: bool, error_message: Optional[str], user: Optional[User])
        """
        try:
            # Validate inputs
            if not username or len(username) < 3 or len(username) > 50:
                return False, "Username must be 3-50 characters", None

            if not email or "@" not in email or len(email) > 120:
                return False, "Invalid email address", None

            # Validate password strength
            is_valid, error_msg = validate_password_strength(password)
            if not is_valid:
                return False, error_msg, None

            # Check if username or email already exists
            existing_user = db_session.query(User).filter(
                (User.username == username) | (User.email == email)
            ).first()

            if existing_user:
                if existing_user.username == username:
                    return False, "Username already exists", None
                return False, "Email already registered", None

            # Hash password
            try:
                password_hash = hash_password(password)
            except ValueError as e:
                return False, str(e), None

            # Create user
            new_user = User(
                username=username,
                email=email,
                password_hash=password_hash,
                full_name=full_name if full_name else "",
                role="student",
                is_active=True,
            )

            db_session.add(new_user)
            db_session.commit()

            logger.info(f"User registered successfully: {username}")
            return True, None, new_user

        except IntegrityError as e:
            db_session.rollback()
            logger.error(f"Database integrity error during registration: {str(e)}")
            return False, "Registration error. Please try again.", None
        except Exception as e:
            db_session.rollback()
            logger.error(f"Unexpected error during registration: {str(e)}")
            return False, "An unexpected error occurred. Please try again.", None

    @staticmethod
    def login_user(
        db_session: SQLSession,
        username: str,
        password: str,
        ip_address: Optional[str] = None,
    ) -> Tuple[bool, Optional[str], Optional[str], Optional[User]]:
        """
        Authenticate user and create session.

        Args:
            db_session: Database session
            username: Username
            password: Password
            ip_address: Client IP address (optional, for security logging)

        Returns:
            Tuple of (success: bool, error_message: Optional[str], token: Optional[str], user: Optional[User])
        """
        try:
            # Find user by username
            user = db_session.query(User).filter_by(username=username).first()

            if not user:
                logger.warning(f"Login attempt with non-existent user: {username}")
                return False, "Invalid username or password", None, None

            if not user.is_active:
                logger.warning(f"Login attempt by inactive user: {username}")
                return False, "Your account is disabled. Please contact support.", None, None

            # Verify password
            if not verify_password(password, user.password_hash):
                logger.warning(f"Failed login attempt for user: {username}")
                return False, "Invalid username or password", None, None

            # Generate session token
            token = SessionManager.generate_token()
            expires_at = SessionManager.generate_expiry_time()

            # Create session record
            session = Session(
                user_id=user.id,
                token=token,
                expires_at=expires_at,
                ip_address=ip_address,
            )

            # Update last login
            user.last_login = datetime.utcnow()

            db_session.add(session)
            db_session.commit()

            logger.info(f"User logged in successfully: {username}")
            return True, None, token, user

        except Exception as e:
            db_session.rollback()
            logger.error(f"Error during login: {str(e)}")
            return False, "An error occurred during login. Please try again.", None, None

    @staticmethod
    def verify_session(db_session: SQLSession, token: str) -> Tuple[bool, Optional[User]]:
        """
        Verify session token and return associated user.

        Args:
            db_session: Database session
            token: Session token

        Returns:
            Tuple of (is_valid: bool, user: Optional[User])
        """
        try:
            # Find session
            session = db_session.query(Session).filter_by(token=token).first()

            if not session:
                return False, None

            # Check if session is valid
            if not session.is_valid():
                return False, None

            # Get user
            user = session.user
            if not user or not user.is_active:
                return False, None

            return True, user

        except Exception as e:
            logger.error(f"Error verifying session: {str(e)}")
            return False, None

    @staticmethod
    def logout_user(db_session: SQLSession, token: str) -> bool:
        """
        Logout user by invalidating their session token.

        Args:
            db_session: Database session
            token: Session token to invalidate

        Returns:
            True if logout successful, False otherwise
        """
        try:
            session = db_session.query(Session).filter_by(token=token).first()

            if session:
                db_session.delete(session)
                db_session.commit()
                logger.info(f"User logged out successfully: user_id={session.user_id}")
                return True

            logger.warning("Logout attempt with invalid token")
            return False

        except Exception as e:
            db_session.rollback()
            logger.error(f"Error during logout: {str(e)}")
            return False

    @staticmethod
    def cleanup_expired_sessions(db_session: SQLSession) -> int:
        """
        Delete all expired sessions.

        Args:
            db_session: Database session

        Returns:
            Number of sessions deleted
        """
        try:
            from datetime import datetime as dt
            sessions_to_delete = db_session.query(Session).filter(
                Session.expires_at < dt.utcnow()
            ).all()

            count = len(sessions_to_delete)
            for session in sessions_to_delete:
                db_session.delete(session)

            db_session.commit()
            logger.info(f"Cleaned up {count} expired sessions")
            return count

        except Exception as e:
            db_session.rollback()
            logger.error(f"Error cleaning up expired sessions: {str(e)}")
            return 0
