"""Database module for IGCSE Tutor."""

from src.database.db_init import (
    DatabaseManager,
    get_db_manager,
    init_database,
    get_session,
    close_database,
)
from src.database.models import (
    Base,
    User,
    Session,
    AuditLog,
    QuizHistory,
    OfflineCache,
    AdminSettings,
)

__all__ = [
    "DatabaseManager",
    "get_db_manager",
    "init_database",
    "get_session",
    "close_database",
    "Base",
    "User",
    "Session",
    "AuditLog",
    "QuizHistory",
    "OfflineCache",
    "AdminSettings",
]
