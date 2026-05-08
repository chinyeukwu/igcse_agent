"""
Security Utilities
Token verification, admin role checks, and security measures.
"""

from fastapi import HTTPException, status
from fastapi.security import HTTPAuthCredentials
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging
import asyncio
from collections import defaultdict

logger = logging.getLogger(__name__)


class SecurityConfig:
    """Security configuration."""
    SECRET_KEY = "your-secret-key-change-in-production"
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 30
    REFRESH_TOKEN_EXPIRE_DAYS = 7
    
    # Rate limiting
    MAX_LOGIN_ATTEMPTS = 5
    LOCKOUT_DURATION_MINUTES = 15
    
    # Admin settings
    REQUIRE_MFA_FOR_ADMIN = True
    ADMIN_SESSION_TIMEOUT_MINUTES = 60


class RateLimiter:
    """Rate limiter for security."""
    
    def __init__(self):
        self.attempts = defaultdict(list)
    
    def is_rate_limited(self, key: str) -> bool:
        """Check if key is rate limited."""
        now = datetime.now()
        cutoff_time = now - timedelta(minutes=SecurityConfig.LOCKOUT_DURATION_MINUTES)
        
        # Clean old attempts
        self.attempts[key] = [
            t for t in self.attempts[key]
            if t > cutoff_time
        ]
        
        return len(self.attempts[key]) >= SecurityConfig.MAX_LOGIN_ATTEMPTS
    
    def record_attempt(self, key: str):
        """Record login attempt."""
        self.attempts[key].append(datetime.now())
    
    def reset_attempts(self, key: str):
        """Reset login attempts."""
        self.attempts[key] = []


# Global rate limiter
rate_limiter = RateLimiter()


class TokenManager:
    """Manages JWT tokens."""
    
    @staticmethod
    def create_access_token(
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create JWT access token."""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                minutes=SecurityConfig.ACCESS_TOKEN_EXPIRE_MINUTES
            )
        
        to_encode.update({"exp": expire, "iat": datetime.utcnow()})
        
        encoded_jwt = jwt.encode(
            to_encode,
            SecurityConfig.SECRET_KEY,
            algorithm=SecurityConfig.ALGORITHM
        )
        return encoded_jwt
    
    @staticmethod
    def verify_token(token: str) -> Dict[str, Any]:
        """Verify and decode JWT token."""
        try:
            payload = jwt.decode(
                token,
                SecurityConfig.SECRET_KEY,
                algorithms=[SecurityConfig.ALGORITHM]
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
    
    @staticmethod
    def create_admin_token(user_id: int, username: str) -> str:
        """Create admin session token."""
        data = {
            "sub": str(user_id),
            "username": username,
            "scope": "admin",
            "type": "access"
        }
        
        expires_delta = timedelta(
            minutes=SecurityConfig.ADMIN_SESSION_TIMEOUT_MINUTES
        )
        
        return TokenManager.create_access_token(data, expires_delta)
    
    @staticmethod
    def is_admin_token(token: str) -> bool:
        """Check if token is for admin."""
        try:
            payload = TokenManager.verify_token(token)
            return payload.get("scope") == "admin"
        except HTTPException:
            return False


async def verify_admin_token(
    token: str,
    db = None
) -> Dict[str, Any]:
    """Verify admin token and return user data."""
    if not TokenManager.is_admin_token(token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    
    try:
        payload = TokenManager.verify_token(token)
        user_id = payload.get("sub")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        # Optionally verify user exists in database
        if db:
            user = await db.get_user(int(user_id))
            if not user or not user.is_admin:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User is not an admin"
                )
        
        return payload
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying admin token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token verification failed"
        )


async def require_admin(
    token: str,
    db = None
):
    """Dependency to require admin privileges."""
    payload = await verify_admin_token(token, db)
    
    # Get user object if database is available
    if db:
        user_id = int(payload.get("sub"))
        user = await db.get_user(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        return user
    
    return payload


def check_rate_limit(identifier: str) -> bool:
    """Check if request is rate limited."""
    if rate_limiter.is_rate_limited(identifier):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many attempts. Try again in {SecurityConfig.LOCKOUT_DURATION_MINUTES} minutes"
        )
    return True


def record_failed_attempt(identifier: str):
    """Record failed login attempt."""
    rate_limiter.record_attempt(identifier)


def reset_rate_limit(identifier: str):
    """Reset rate limit for identifier."""
    rate_limiter.reset_attempts(identifier)


class AuditLogger:
    """Audit logging for security events."""
    
    @staticmethod
    async def log_admin_action(
        admin_id: int,
        action: str,
        resource: str,
        details: Dict[str, Any],
        status: str = "success",
        db = None
    ):
        """Log administrative action."""
        log_entry = {
            "timestamp": datetime.now(),
            "admin_id": admin_id,
            "action": action,
            "resource": resource,
            "details": details,
            "status": status
        }
        
        logger.info(f"Admin action: {action} on {resource} by admin {admin_id}")
        
        # Save to database if available
        if db:
            try:
                await db.save_audit_log(log_entry)
            except Exception as e:
                logger.error(f"Error saving audit log: {str(e)}")
    
    @staticmethod
    async def log_security_event(
        event_type: str,
        severity: str,
        user_id: Optional[int] = None,
        details: Dict[str, Any] = None,
        db = None
    ):
        """Log security event."""
        log_entry = {
            "timestamp": datetime.now(),
            "event_type": event_type,
            "severity": severity,
            "user_id": user_id,
            "details": details or {}
        }
        
        logger.warning(f"Security event: {event_type} (severity: {severity})")
        
        # Save to database if available
        if db:
            try:
                await db.save_security_alert(log_entry)
            except Exception as e:
                logger.error(f"Error saving security alert: {str(e)}")


class PermissionValidator:
    """Validates user permissions."""
    
    @staticmethod
    def require_admin(user) -> bool:
        """Check if user is admin."""
        if not hasattr(user, 'is_admin') or not user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin privileges required"
            )
        return True
    
    @staticmethod
    def require_active(user) -> bool:
        """Check if user account is active."""
        if not hasattr(user, 'is_active') or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive"
            )
        return True
    
    @staticmethod
    def require_own_data_or_admin(user, target_user_id: int) -> bool:
        """Check if user owns data or is admin."""
        if user.id != target_user_id and not user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return True


class PasswordValidator:
    """Validates password strength."""
    
    @staticmethod
    def validate_password(password: str) -> tuple[bool, str]:
        """
        Validate password meets requirements.
        
        Returns:
            (is_valid, error_message)
        """
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"
        
        if not any(c.isupper() for c in password):
            return False, "Password must contain uppercase letter"
        
        if not any(c.islower() for c in password):
            return False, "Password must contain lowercase letter"
        
        if not any(c.isdigit() for c in password):
            return False, "Password must contain digit"
        
        if not any(c in "!@#$%^&*" for c in password):
            return False, "Password must contain special character (!@#$%^&*)"
        
        return True, ""


class MFAHandler:
    """Handles multi-factor authentication."""
    
    @staticmethod
    def generate_mfa_code() -> str:
        """Generate MFA code."""
        import random
        return ''.join([str(random.randint(0, 9)) for _ in range(6)])
    
    @staticmethod
    def verify_mfa_code(provided_code: str, stored_code: str, max_age_seconds: int = 300) -> bool:
        """Verify MFA code."""
        # In production, implement proper time-based or event-based MFA
        return provided_code == stored_code


class SessionManager:
    """Manages admin sessions."""
    
    def __init__(self):
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
    
    def create_session(self, user_id: int, token: str, ip_address: str) -> str:
        """Create new admin session."""
        session_id = f"{user_id}_{datetime.now().timestamp()}"
        
        self.active_sessions[session_id] = {
            "user_id": user_id,
            "token": token,
            "ip_address": ip_address,
            "created_at": datetime.now(),
            "last_activity": datetime.now()
        }
        
        return session_id
    
    def validate_session(self, session_id: str, current_ip: str) -> bool:
        """Validate admin session."""
        if session_id not in self.active_sessions:
            return False
        
        session = self.active_sessions[session_id]
        
        # Check IP address
        if session["ip_address"] != current_ip:
            logger.warning(f"Session IP mismatch for session {session_id}")
            return False
        
        # Check session timeout
        timeout_delta = timedelta(
            minutes=SecurityConfig.ADMIN_SESSION_TIMEOUT_MINUTES
        )
        if datetime.now() - session["last_activity"] > timeout_delta:
            del self.active_sessions[session_id]
            return False
        
        # Update last activity
        session["last_activity"] = datetime.now()
        return True
    
    def terminate_session(self, session_id: str):
        """Terminate admin session."""
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]


# Global session manager
session_manager = SessionManager()
