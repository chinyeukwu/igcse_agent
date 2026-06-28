"""
SQLAlchemy ORM models for IGCSE Tutor application.
Follows SonarQube standards for security, maintainability, and reliability.
"""

from datetime import datetime, timedelta
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Float, Index
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class User(Base):
    """User model for authentication and profile management."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(120), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(120), nullable=True)
    role = Column(String(20), default="student", nullable=False)  # student|admin
    theme_preference = Column(String(20), default="light", nullable=False)  # light|dark
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_login = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")
    quiz_histories = relationship("QuizHistory", back_populates="user", cascade="all, delete-orphan")
    chat_messages = relationship("ChatHistory", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        """Return string representation of User."""
        return f"<User(id={self.id}, username={self.username}, role={self.role})>"


class Session(Base):
    """Session model for user authentication tokens."""

    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    token = Column(String(500), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    ip_address = Column(String(45), nullable=True)  # IPv4/IPv6

    # Relationships
    user = relationship("User", back_populates="sessions")

    def is_valid(self) -> bool:
        """Check if session token is still valid (not expired)."""
        return datetime.utcnow() < self.expires_at

    def __repr__(self) -> str:
        """Return string representation of Session."""
        return f"<Session(id={self.id}, user_id={self.user_id}, is_valid={self.is_valid()})>"


# Index for efficiently querying active sessions
__session_index = Index("ix_session_user_expires", Session.user_id, Session.expires_at)


class AuditLog(Base):
    """Audit log model for tracking all user queries and system events."""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    query_text = Column(Text, nullable=False)  # Sanitized query
    subject = Column(String(50), nullable=True)  # Math|English|French|Science|FineArts
    tool_used = Column(String(50), nullable=True)  # french_tool|igcse_tool|quiz_tool
    response_length = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    is_injection_flagged = Column(Boolean, default=False, nullable=False)
    is_out_of_scope = Column(Boolean, default=False, nullable=False)
    error_message = Column(String(500), nullable=True)

    # Relationships
    user = relationship("User", back_populates="audit_logs")

    def __repr__(self) -> str:
        """Return string representation of AuditLog."""
        return f"<AuditLog(id={self.id}, user_id={self.user_id}, subject={self.subject})>"


# Composite index for efficient user query lookups
__auditlog_index = Index("ix_auditlog_user_created", AuditLog.user_id, AuditLog.created_at)


class QuizHistory(Base):
    """Quiz history model for tracking user quiz attempts with 60-day retention."""

    __tablename__ = "quiz_history"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    subject = Column(String(50), nullable=False)  # Math|English|French|Science|FineArts
    topic = Column(String(150), nullable=False)
    difficulty = Column(String(20), nullable=False)  # easy|medium|hard
    language_code = Column(String(5), default="en", nullable=False)  # Future: multi-language support
    questions_json = Column(Text, nullable=False)  # JSON-serialized questions
    user_answers_json = Column(Text, nullable=False)  # JSON-serialized answers
    score = Column(Float, nullable=False)  # 0-100
    time_taken_seconds = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    is_offline = Column(Boolean, default=False, nullable=False)  # Generated without internet
    synced_at = Column(DateTime, nullable=True)  # When synced to server

    # Relationships
    user = relationship("User", back_populates="quiz_histories")

    def is_within_retention(self) -> bool:
        """Check if quiz history is within 60-day retention period."""
        retention_date = datetime.utcnow() - timedelta(days=60)
        return self.created_at > retention_date

    def __repr__(self) -> str:
        """Return string representation of QuizHistory."""
        return f"<QuizHistory(id={self.id}, user_id={self.user_id}, subject={self.subject}, score={self.score})>"


# Composite index for efficient user quiz lookups
__quizhistory_index = Index("ix_quizhistory_user_created", QuizHistory.user_id, QuizHistory.created_at)


class OfflineCache(Base):
    """Offline cache model for storing responses for offline access."""

    __tablename__ = "offline_cache"

    id = Column(Integer, primary_key=True)
    cache_key = Column(String(255), unique=True, nullable=False, index=True)
    response_json = Column(Text, nullable=False)
    subject = Column(String(50), nullable=False)
    language_code = Column(String(5), default="en", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)

    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        return datetime.utcnow() > self.expires_at

    def __repr__(self) -> str:
        """Return string representation of OfflineCache."""
        return f"<OfflineCache(id={self.id}, subject={self.subject})>"


class ChatHistory(Base):
    """Chat history model for storing user conversations."""

    __tablename__ = "chat_history"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    session_id = Column(String(100), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # user|assistant
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    user = relationship("User", backref="chat_messages")

    def __repr__(self) -> str:
        """Return string representation of ChatHistory."""
        return f"<ChatHistory(id={self.id}, user_id={self.user_id}, role={self.role})>"


# Composite index for efficient user chat lookups
__chathist_index = Index("ix_chathist_user_session", ChatHistory.user_id, ChatHistory.session_id)


class AdminSettings(Base):
    """Admin settings model for system configuration."""

    __tablename__ = "admin_settings"

    id = Column(Integer, primary_key=True)
    setting_key = Column(String(100), unique=True, nullable=False, index=True)
    setting_value = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        """Return string representation of AdminSettings."""
        return f"<AdminSettings(setting_key={self.setting_key})>"


class PaperQuestion(Base):
    """Individual questions extracted from Pearson exam papers."""

    __tablename__ = "paper_questions"

    id = Column(Integer, primary_key=True)
    paper_code = Column(String(10), nullable=False, index=True)  # 4ma1, 4ea1, etc.
    paper_number = Column(Integer, nullable=False)  # Paper 1, 2, etc.
    subject = Column(String(50), nullable=False, index=True)  # Maths, English, etc.
    question_number = Column(Integer, nullable=False)  # Q1, Q2, etc.
    question_text = Column(Text, nullable=False)
    question_type = Column(String(50), nullable=True)  # multiple_choice, short_answer, essay, etc.
    options_json = Column(Text, nullable=True)  # JSON for multiple choice
    correct_answer = Column(Text, nullable=True)
    marking_scheme = Column(Text, nullable=True)  # Detailed marking criteria
    marks_total = Column(Integer, nullable=True)  # Total marks for question
    source_filename = Column(String(255), nullable=False)  # Which PDF file
    page_number = Column(Integer, nullable=True)
    difficulty_level = Column(String(20), default="medium", nullable=False)  # easy, medium, hard
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        """Return string representation of PaperQuestion."""
        return f"<PaperQuestion(id={self.id}, paper_code={self.paper_code}, q={self.question_number})>"


class QuizAttempt(Base):
    """Detailed quiz attempt record."""

    __tablename__ = "quiz_attempts"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    subject = Column(String(50), nullable=False, index=True)
    difficulty_level = Column(String(20), nullable=False)  # easy, medium, hard
    question_count = Column(Integer, nullable=False)
    score_percentage = Column(Float, nullable=False)  # 0-100
    time_taken_seconds = Column(Integer, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    status = Column(String(20), default="in_progress", nullable=False)  # in_progress, completed, abandoned

    # Relationships
    user = relationship("User", backref="quiz_attempts")
    student_answers = relationship("StudentAnswer", back_populates="quiz_attempt", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        """Return string representation of QuizAttempt."""
        return f"<QuizAttempt(id={self.id}, user_id={self.user_id}, score={self.score_percentage})>"


# Composite index for efficient user quiz lookups
__quizattempt_index = Index("ix_quizattempt_user_created", QuizAttempt.user_id, QuizAttempt.started_at)


class StudentAnswer(Base):
    """Individual student answer to a quiz question."""

    __tablename__ = "student_answers"

    id = Column(Integer, primary_key=True)
    quiz_attempt_id = Column(Integer, ForeignKey("quiz_attempts.id"), nullable=False, index=True)
    question_id = Column(Integer, ForeignKey("paper_questions.id"), nullable=True, index=True)
    question_text = Column(Text, nullable=False)  # Copy of question for historical tracking
    student_answer = Column(Text, nullable=False)
    correct_answer = Column(Text, nullable=False)
    is_correct = Column(Boolean, nullable=False)
    score_earned = Column(Float, nullable=False)  # Points earned (0 to marks_total)
    marks_total = Column(Float, nullable=False)  # Total points available
    feedback = Column(Text, nullable=True)  # Marking scheme feedback
    time_spent_seconds = Column(Integer, nullable=True)  # Time spent on this question
    attempted_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    quiz_attempt = relationship("QuizAttempt", back_populates="student_answers")
    paper_question = relationship("PaperQuestion")

    def __repr__(self) -> str:
        """Return string representation of StudentAnswer."""
        return f"<StudentAnswer(id={self.id}, score={self.score_earned}/{self.marks_total})>"


class StudentDifficultyProfile(Base):
    """Adaptive difficulty calibration profile for each student per subject."""

    __tablename__ = "student_difficulty_profiles"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    subject = Column(String(50), nullable=False, index=True)
    current_difficulty = Column(String(20), default="easy", nullable=False)  # easy, medium, hard
    accuracy_rate = Column(Float, default=0.0, nullable=False)  # 0-100%
    quizzes_completed = Column(Integer, default=0, nullable=False)
    consecutive_correct = Column(Integer, default=0, nullable=False)
    last_quiz_score = Column(Float, nullable=True)
    average_score = Column(Float, nullable=True)  # Moving average
    last_updated = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", backref="difficulty_profiles")

    def should_increase_difficulty(self) -> bool:
        """Check if student should be moved to harder difficulty."""
        return self.accuracy_rate >= 80.0 and self.consecutive_correct >= 2

    def should_decrease_difficulty(self) -> bool:
        """Check if student should be moved to easier difficulty."""
        return self.accuracy_rate < 50.0 and self.current_difficulty != "easy"

    def __repr__(self) -> str:
        """Return string representation of StudentDifficultyProfile."""
        return f"<StudentDifficultyProfile(user_id={self.user_id}, subject={self.subject}, difficulty={self.current_difficulty})>"


# Composite index for efficient student profile lookups
__studentprofile_index = Index("ix_studentprofile_user_subject", StudentDifficultyProfile.user_id, StudentDifficultyProfile.subject)
