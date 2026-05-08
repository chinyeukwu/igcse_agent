"""
Configuration module for IGCSE Tutor application.
Loads settings from environment variables with sensible defaults.
Follows SonarQube standards for secure configuration management.
"""

import os
from pathlib import Path

# ===== API Configuration =====
openai_key = os.getenv("OPENAI_API_KEY")
fastapi_url = os.getenv("FASTAPI_URL", "http://localhost:8000")
fastapi_host = os.getenv("FASTAPI_HOST", "0.0.0.0")
fastapi_port = int(os.getenv("FASTAPI_PORT", 8000))

# ===== Database Configuration =====
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Database path (SQLite)
database_path = os.getenv("DATABASE_PATH", str(DATA_DIR / "igcse_tutor.db"))

# ===== Authentication Configuration =====
# Token expiration time in hours
token_expiry_hours = int(os.getenv("TOKEN_EXPIRY_HOURS", 24))

# Session cleanup interval in hours (delete expired sessions)
session_cleanup_interval = int(os.getenv("SESSION_CLEANUP_INTERVAL", 24))

# Maximum login attempts before lockout
max_login_attempts = int(os.getenv("MAX_LOGIN_ATTEMPTS", 5))

# Password requirements (SonarQube S2053 compliance)
min_password_length = int(os.getenv("MIN_PASSWORD_LENGTH", 8))
require_password_complexity = os.getenv("REQUIRE_PASSWORD_COMPLEXITY", "true").lower() == "true"

# ===== Data File Configuration =====
default_data_path = os.path.join(BASE_DIR, "src/data", "premier-league-matches.csv")
file_path = os.getenv("DATA_FILE_PATH", default_data_path)

# ===== External Services =====
football_website = os.getenv("FOOTBALL_WEBSITE", "https://www.premierleague.com/")

# ===== Feature Flags =====
# Offline mode support
enable_offline_mode = os.getenv("ENABLE_OFFLINE_MODE", "true").lower() == "true"

# Quiz generation (fresh each time)
enable_quiz_generation = os.getenv("ENABLE_QUIZ_GENERATION", "true").lower() == "true"

# Admin panel access
enable_admin_panel = os.getenv("ENABLE_ADMIN_PANEL", "true").lower() == "true"

# Quiz history retention in days
quiz_history_retention_days = int(os.getenv("QUIZ_HISTORY_RETENTION_DAYS", 60))

# Audit log retention in days
audit_log_retention_days = int(os.getenv("AUDIT_LOG_RETENTION_DAYS", 90))

# ===== Security Configuration =====
# Enable prompt injection detection
enable_injection_detection = os.getenv("ENABLE_INJECTION_DETECTION", "true").lower() == "true"

# Enable response validation
enable_response_validation = os.getenv("ENABLE_RESPONSE_VALIDATION", "true").lower() == "true"

# Maximum query length (characters)
max_query_length = int(os.getenv("MAX_QUERY_LENGTH", 1000))

# Offline cache expiry in hours
offline_cache_expiry_hours = int(os.getenv("OFFLINE_CACHE_EXPIRY_HOURS", 7 * 24))  # 7 days

# ===== Logging Configuration =====
log_level = os.getenv("LOG_LEVEL", "INFO")
log_file = os.getenv("LOG_FILE", str(DATA_DIR / "igcse_tutor.log"))

# ===== Development Settings =====
debug_mode = os.getenv("DEBUG_MODE", "false").lower() == "true"
sql_echo = os.getenv("SQL_ECHO", "false").lower() == "true"