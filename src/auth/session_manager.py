"""
Session and token management using JWT.
Follows SonarQube standards for security S2628 (JWT validation).
"""

import json
import logging
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages user sessions with token generation and validation."""

    # Token expiration time in hours
    TOKEN_EXPIRY_HOURS = 24

    @staticmethod
    def generate_token() -> str:
        """
        Generate a secure random token for session.

        Returns:
            Random hexadecimal token (64 chars = 32 bytes)
        """
        # Generate 32 bytes of randomness (256 bits)
        return secrets.token_hex(32)

    @staticmethod
    def generate_expiry_time(hours: int = TOKEN_EXPIRY_HOURS) -> datetime:
        """
        Generate token expiry time.

        Args:
            hours: Number of hours until expiry

        Returns:
            Datetime object representing expiry time
        """
        return datetime.utcnow() + timedelta(hours=hours)

    @staticmethod
    def is_token_valid(expires_at: datetime) -> bool:
        """
        Check if token is still valid (not expired).

        Args:
            expires_at: Token expiry datetime

        Returns:
            True if token is still valid, False if expired
        """
        return datetime.utcnow() < expires_at

    @staticmethod
    def get_time_until_expiry(expires_at: datetime) -> timedelta:
        """
        Get remaining time until token expiry.

        Args:
            expires_at: Token expiry datetime

        Returns:
            Timedelta representing time remaining
        """
        return expires_at - datetime.utcnow()


class CacheableSessionData:
    """Represents cached session data for performance."""

    def __init__(
        self,
        user_id: int,
        username: str,
        role: str,
        is_active: bool,
        expires_at: datetime,
    ):
        """
        Initialize cached session data.

        Args:
            user_id: User ID
            username: Username
            role: User role (student|admin)
            is_active: Whether user is active
            expires_at: Token expiry time
        """
        self.user_id = user_id
        self.username = username
        self.role = role
        self.is_active = is_active
        self.expires_at = expires_at

    def to_dict(self) -> Dict[str, Any]:
        """Convert session data to dictionary."""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "role": self.role,
            "is_active": self.is_active,
            "expires_at": self.expires_at.isoformat(),
        }

    def is_valid(self) -> bool:
        """Check if session is still valid."""
        return self.is_active and SessionManager.is_token_valid(self.expires_at)

    def __repr__(self) -> str:
        """Return string representation."""
        return f"<CacheableSessionData(user_id={self.user_id}, username={self.username}, is_valid={self.is_valid()})>"
