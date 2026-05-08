"""
Database initialization and connection management.
Follows SonarQube standards for security and resource management.
"""

import logging
from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session as SQLSession
from sqlalchemy.pool import StaticPool
from contextlib import contextmanager
import os

from src.database.models import Base

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connection, initialization, and session lifecycle."""

    def __init__(self, db_path: str | None = None):
        """
        Initialize database manager.

        Args:
            db_path: Path to SQLite database file. If None, uses default location.
        """
        if db_path is None:
            db_path = self._get_default_db_path()

        self.db_path = db_path
        self.engine = None
        self.SessionLocal = None
        self._initialize_engine()

    @staticmethod
    def _get_default_db_path() -> str:
        """Get default database path in project root."""
        base_dir = Path(__file__).resolve().parent.parent.parent
        db_dir = base_dir / "data"
        db_dir.mkdir(parents=True, exist_ok=True)
        return str(db_dir / "igcse_tutor.db")

    def _initialize_engine(self) -> None:
        """Initialize SQLAlchemy engine with proper configuration."""
        try:
            # Create SQLite database URL
            db_url = f"sqlite:///{self.db_path}"

            # Enable foreign keys for SQLite (important for data integrity)
            self.engine = create_engine(
                db_url,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
                echo=False,  # Set to True for SQL query logging
            )

            # Enable foreign key constraints
            @event.listens_for(self.engine, "connect")
            def set_sqlite_pragma(dbapi_conn, connection_record):
                """Enable foreign key support in SQLite."""
                cursor = dbapi_conn.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()

            # Create session factory
            self.SessionLocal = sessionmaker(
                autocommit=False, autoflush=False, bind=self.engine
            )

            logger.info(f"Database engine initialized: {self.db_path}")

        except Exception as e:
            logger.error(f"Failed to initialize database engine: {str(e)}")
            raise

    def init_db(self) -> None:
        """Create all database tables."""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database tables: {str(e)}")
            raise

    @contextmanager
    def get_session(self):
        """
        Provide a database session context manager.

        Yields:
            SQLAlchemy Session object

        Example:
            with db_manager.get_session() as session:
                user = session.query(User).filter_by(username="john").first()
        """
        if self.SessionLocal is None:
            raise RuntimeError("Database not initialized. Call init_db() first.")

        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {str(e)}")
            raise
        finally:
            session.close()

    def close(self) -> None:
        """Close database connection pool."""
        if self.engine:
            self.engine.dispose()
            logger.info("Database connection closed")


# Global database manager instance
_db_manager: DatabaseManager | None = None


def get_db_manager() -> DatabaseManager:
    """Get or create global database manager instance."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


def init_database() -> None:
    """Initialize database (create tables)."""
    db_manager = get_db_manager()
    db_manager.init_db()


def get_session() -> SQLSession:
    """Get a new database session."""
    db_manager = get_db_manager()
    return db_manager.SessionLocal()


def close_database() -> None:
    """Close database connections."""
    global _db_manager
    if _db_manager:
        _db_manager.close()
        _db_manager = None
