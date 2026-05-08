"""
Password hashing and verification utilities.
Uses bcrypt for secure password handling - follows SonarQube S2053 standard.
"""

import logging
import bcrypt
from typing import Optional

logger = logging.getLogger(__name__)

# Bcrypt cost factor (higher = slower, more secure, but more computationally expensive)
# 12 is a good balance between security and performance (as of 2024)
BCRYPT_COST = 12


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: Plain text password to hash

    Returns:
        BCrypt hashed password (includes salt)

    Raises:
        ValueError: If password is empty or invalid
    """
    if not password or not isinstance(password, str):
        raise ValueError("Password must be a non-empty string")

    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")

    if len(password) > 128:
        raise ValueError("Password must not exceed 128 characters")

    try:
        salt = bcrypt.gensalt(rounds=BCRYPT_COST)
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
        return hashed.decode("utf-8")
    except Exception as e:
        logger.error(f"Error hashing password: {str(e)}")
        raise ValueError("Failed to hash password") from e


def verify_password(password: str, password_hash: str) -> bool:
    """
    Verify a password against its hash.

    Args:
        password: Plain text password to verify
        password_hash: BCrypt hashed password

    Returns:
        True if password matches hash, False otherwise
    """
    if not password or not password_hash:
        return False

    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except Exception as e:
        logger.error(f"Error verifying password: {str(e)}")
        return False


def validate_password_strength(password: str) -> tuple[bool, Optional[str]]:
    """
    Validate password meets security requirements.

    Args:
        password: Password to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not password:
        return False, "Password is required"

    if len(password) < 8:
        return False, "Password must be at least 8 characters long"

    if len(password) > 128:
        return False, "Password must not exceed 128 characters"

    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)

    if not (has_upper and has_lower and has_digit):
        return (
            False,
            "Password must contain uppercase, lowercase, and digit characters",
        )

    return True, None
