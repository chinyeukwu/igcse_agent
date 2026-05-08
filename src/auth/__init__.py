"""Authentication module for IGCSE Tutor."""

from src.auth.password_utils import (
    hash_password,
    verify_password,
    validate_password_strength,
)
from src.auth.session_manager import SessionManager, CacheableSessionData
from src.auth.user_service import UserService

__all__ = [
    "hash_password",
    "verify_password",
    "validate_password_strength",
    "SessionManager",
    "CacheableSessionData",
    "UserService",
]
