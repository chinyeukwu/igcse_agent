"""
FastAPI main application with authentication and agent integration.
Follows SonarQube standards for security S2053, S2629, S4502.
"""

import asyncio
import logging
import sys
import os
import time
import re
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, status, Depends, HTTPException, Header, Request
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel, EmailStr, field_validator
from langchain_core.messages import HumanMessage
from pathlib import Path

from src.agents.orchestrator import create_agent
from src.database import get_db_manager, init_database, get_session
from src.auth import UserService
from src.security import InputValidator, ResponseValidator, AuditLogger
from src.offline import CacheManager, SyncManager, StatusDetector
from src.quiz import QuizGenerator, QuizService
from src.admin import AdminService
from src.services import (
    QuizScoringService,
    DifficultyCalibrationService,
    QuizAttemptService,
    EssayEvaluationService,
    TopicPerformanceService,
    SpacedRepetitionService,
    PracticePlanService,
    NotificationService,
    NotificationPreferences
)
from src.database.models import QuizAttempt, StudentAnswer, StudentDifficultyProfile, User, NotificationHistory, Session
from src.auth.password_utils import hash_password

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def clean_response(text: str) -> str:
    """Clean LaTeX notation and unwanted characters from responses."""
    if not text:
        return text

    # Remove LaTeX inline math: \( ... \)
    text = re.sub(r'\\\(\s*(.*?)\s*\\\)', r'\1', text, flags=re.DOTALL)

    # Remove LaTeX display math: \[ ... \]
    text = re.sub(r'\\\[\s*(.*?)\s*\\\]', r'\1', text, flags=re.DOTALL)

    # Remove LaTeX inline math: $ ... $ (single $)
    text = re.sub(r'\$\s*(.*?)\s*\$', r'\1', text, flags=re.DOTALL)

    # Remove LaTeX display math: $$ ... $$
    text = re.sub(r'\$\$\s*(.*?)\s*\$\$', r'\1', text, flags=re.DOTALL)

    # Remove \text{...} commands, keeping content
    text = re.sub(r'\\text\{([^}]*)\}', r'\1', text)

    # Remove \mathrm{...} and similar commands, keeping content
    text = re.sub(r'\\mathrm\{([^}]*)\}', r'\1', text)
    text = re.sub(r'\\mathbf\{([^}]*)\}', r'\1', text)
    text = re.sub(r'\\mathit\{([^}]*)\}', r'\1', text)

    # Replace LaTeX symbols with Unicode equivalents
    replacements = {
        r'\\rightarrow': '→',
        r'\\leftarrow': '←',
        r'\\leftrightarrow': '↔',
        r'\\Rightarrow': '⇒',
        r'\\Leftarrow': '⇐',
        r'\\approx': '≈',
        r'\\times': '×',
        r'\\cdot': '·',
        r'\\div': '÷',
        r'\\pm': '±',
        r'\\mp': '∓',
        r'\\geq': '≥',
        r'\\leq': '≤',
        r'\\ne': '≠',
        r'\\equiv': '≡',
        r'\\infty': '∞',
        r'\\alpha': 'α',
        r'\\beta': 'β',
        r'\\gamma': 'γ',
        r'\\delta': 'δ',
        r'\\theta': 'θ',
        r'\\pi': 'π',
    }
    for latex, unicode_char in replacements.items():
        text = re.sub(latex, unicode_char, text)

    # Remove \sqrt{...} but keep content
    text = re.sub(r'\\sqrt\{([^}]*)\}', r'√(\1)', text)

    # Remove \frac{...}{...} and simplify
    text = re.sub(r'\\frac\{([^}]*)\}\{([^}]*)\}', r'\1/\2', text)

    # Remove remaining LaTeX commands (anything starting with backslash)
    text = re.sub(r'\\[a-zA-Z_]+(\{[^}]*\})?', '', text)

    # Remove remaining curly braces that may be left from LaTeX
    text = re.sub(r'[{}]', '', text)

    # Clean excessive whitespace
    text = re.sub(r'\n\s*\n', '\n\n', text)
    text = re.sub(r' +', ' ', text)

    return text.strip()


# ===== Request/Response Models =====

class UserRegisterInput(BaseModel):
    """User registration request model."""
    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None

    @field_validator("username")
    def validate_username(cls, v):
        """Validate username format."""
        if not v or len(v) < 3 or len(v) > 50:
            raise ValueError("Username must be 3-50 characters")
        if not v.isalnum():
            raise ValueError("Username must contain only alphanumeric characters")
        return v

    @field_validator("password")
    def validate_password(cls, v):
        """Validate password format."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class UserLoginInput(BaseModel):
    """User login request model."""
    username: str
    password: str


class QueryInput(BaseModel):
    """Query request model."""
    query: str
    subject: Optional[str] = None
    difficulty: Optional[str] = None

    @field_validator("query")
    def validate_query(cls, v):
        """Validate query length."""
        if not v or len(v) > 1000:
            raise ValueError("Query must be between 1 and 1000 characters")
        return v


class QuizGenerateInput(BaseModel):
    """Quiz generation request model."""
    subject: str
    difficulty: str = "medium"
    question_count: int = 5
    topic: Optional[str] = "IGCSE Practice"
    exclude_questions: Optional[list] = None  # List of question texts to exclude

    @field_validator("subject")
    def validate_subject(cls, v):
        """Validate subject."""
        valid_subjects = ["maths", "english", "french", "science", "finearts"]
        if v.lower() not in valid_subjects:
            raise ValueError(f"Subject must be one of: {', '.join(valid_subjects)}")
        return v.lower()

    @field_validator("difficulty")
    def validate_difficulty(cls, v):
        """Validate difficulty."""
        valid_difficulties = ["easy", "medium", "hard"]
        if v.lower() not in valid_difficulties:
            raise ValueError(f"Difficulty must be one of: {', '.join(valid_difficulties)}")
        return v.lower()

    @field_validator("question_count")
    def validate_question_count(cls, v):
        """Validate question count."""
        valid_counts = [3, 5, 10]
        if v not in valid_counts:
            raise ValueError(f"Question count must be one of: {', '.join(map(str, valid_counts))}")
        return v


class QuizSubmitInput(BaseModel):
    """Quiz submission request model."""
    subject: str
    difficulty: str
    topic: str
    questions: list  # Raw questions from generation
    user_answers: list  # List of answer indices (0-3)
    time_taken_seconds: Optional[int] = None


class QuizAttemptStartInput(BaseModel):
    """Start a new quiz attempt."""
    subject: str
    difficulty: Optional[str] = None  # If None, use recommended from profile
    question_count: int = 5


class QuestionAnswerInput(BaseModel):
    """Submit an answer to a question during quiz."""
    quiz_attempt_id: int
    question_number: int
    student_answer: str
    correct_answer: Optional[str] = None  # If provided, answer is graded against it
    time_spent_seconds: Optional[int] = None


class QuizAttemptCompleteInput(BaseModel):
    """Complete a quiz attempt."""
    quiz_attempt_id: int
    total_time_seconds: Optional[int] = None


class EssayEvaluationInput(BaseModel):
    """Evaluate an essay-type answer."""
    student_essay: str
    question_text: str
    model_answer: str
    marking_scheme: str
    marks_total: int = 10
    subject: str = "English"
    difficulty: str = "medium"


class AdminUserActionInput(BaseModel):
    """Admin user action request model."""
    action: str  # enable, disable, reset_password, deactivate
    reason: Optional[str] = None


class AdminCleanupInput(BaseModel):
    """Admin cleanup request model."""
    resource_type: str  # cache or audit_logs
    older_than_days: int = 7


class AdminDataExportInput(BaseModel):
    """Admin data export request model."""
    user_id: int
    format: str = "json"  # json or csv


class NotificationPreferenceInput(BaseModel):
    """Notification preference update model."""
    email_enabled: Optional[bool] = None
    sms_enabled: Optional[bool] = None
    email_frequency: Optional[str] = None
    sms_frequency: Optional[str] = None
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None


class SendNotificationInput(BaseModel):
    """Send notification request model."""
    user_id: int
    subject: str = "Maths"
    notification_type: str = "email"


# ===== Dependency Injection =====

def get_auth_token(authorization: Optional[str] = Header(None)) -> str:
    """
    Extract and validate authentication token from header.

    Args:
        authorization: Authorization header value

    Returns:
        Valid token

    Raises:
        HTTPException: If token is invalid or missing
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header",
        )

    token = authorization.split(" ")[1]
    if not token or len(token) != 64:  # Token should be 64 hex chars
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format",
        )

    return token


def get_current_user(token: str = Depends(get_auth_token)):
    """
    Get current authenticated user from token.

    Args:
        token: Authentication token

    Returns:
        Authenticated user

    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        db_session = get_session()
        is_valid, user = UserService.verify_session(db_session, token)

        if not is_valid or not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            )

        return user

    except Exception as e:
        logger.error(f"Error verifying user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
        )


# ===== Logging Middleware =====

class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log HTTP requests and responses."""

    async def dispatch(self, request: Request, call_next):
        """Log request/response with timing information."""
        start_time = time.time()
        method = request.method
        path = request.url.path
        client = request.client.host if request.client else "unknown"

        try:
            response = await call_next(request)
            duration = time.time() - start_time

            # Log based on status code
            if response.status_code >= 500:
                logger.error(
                    f"{method} {path} | Status: {response.status_code} | "
                    f"Duration: {duration:.2f}s | Client: {client}"
                )
            elif response.status_code >= 400:
                logger.warning(
                    f"{method} {path} | Status: {response.status_code} | "
                    f"Duration: {duration:.2f}s | Client: {client}"
                )
            elif duration > 5:  # Log slow requests
                logger.warning(
                    f"{method} {path} | Status: {response.status_code} | "
                    f"Duration: {duration:.2f}s (SLOW) | Client: {client}"
                )
            else:
                logger.debug(
                    f"{method} {path} | Status: {response.status_code} | "
                    f"Duration: {duration:.2f}s | Client: {client}"
                )

            return response
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"{method} {path} | Error: {str(e)} | "
                f"Duration: {duration:.2f}s | Client: {client}"
            )
            raise


# ===== Application Lifecycle =====

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown."""
    # Startup
    logger.info("Initializing database...")
    try:
        init_database()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        raise

    # Optionally start the background notification scheduler.
    # Opt-in via ENABLE_NOTIFICATION_SCHEDULER=true; no-ops cleanly if APScheduler
    # is not installed. Kept off by default to avoid unsolicited emails.
    app.state.notification_scheduler = None
    if os.getenv("ENABLE_NOTIFICATION_SCHEDULER", "false").lower() == "true":
        try:
            from src.services.notification_scheduler import NotificationScheduler
            scheduler = NotificationScheduler()
            if scheduler.start():
                app.state.notification_scheduler = scheduler
        except Exception as e:
            logger.error(f"Failed to start notification scheduler: {str(e)}")

    yield

    # Shutdown
    logger.info("Application shutting down...")
    if getattr(app.state, "notification_scheduler", None):
        try:
            app.state.notification_scheduler.stop()
        except Exception as e:
            logger.warning(f"Error stopping notification scheduler: {str(e)}")
    from src.database import close_database
    close_database()


# ===== FastAPI App =====

app = FastAPI(
    title="IGCSE Tutor API",
    description="API for IGCSE educational tutor with authentication",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:8501",
        "http://192.168.0.109:8000",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# Add logging middleware
app.add_middleware(LoggingMiddleware)

# ===== Static Files & Frontend Routes =====

# Serve static files (CSS, JS, etc.) from src/frontend
frontend_path = Path(__file__).parent / "frontend"
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main chat interface."""
    chat_file = frontend_path / "chat_interface.html"
    if chat_file.exists():
        return FileResponse(chat_file)
    return HTMLResponse("<h1>Chat Interface Not Found</h1>", status_code=404)

@app.get("/login", response_class=HTMLResponse)
async def login_page():
    """Serve the login / registration page."""
    login_file = frontend_path / "login_page.html"
    if login_file.exists():
        return FileResponse(login_file)
    return HTMLResponse("<h1>Login Page Not Found</h1>", status_code=404)

@app.get("/quiz", response_class=HTMLResponse)
async def quiz_page():
    """Serve the quiz interface."""
    quiz_file = frontend_path / "quiz_interface.html"
    if quiz_file.exists():
        return FileResponse(quiz_file)
    return HTMLResponse("<h1>Quiz Interface Not Found</h1>", status_code=404)

@app.get("/chat", response_class=HTMLResponse)
async def chat_page():
    """Serve the chat interface."""
    chat_file = frontend_path / "chat_interface.html"
    if chat_file.exists():
        return FileResponse(chat_file)
    return HTMLResponse("<h1>Chat Interface Not Found</h1>", status_code=404)

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page():
    """Serve the student dashboard."""
    dashboard_file = frontend_path / "student_dashboard.html"
    if dashboard_file.exists():
        return FileResponse(dashboard_file)
    return HTMLResponse("<h1>Dashboard Not Found</h1>", status_code=404)

@app.get("/profile", response_class=HTMLResponse)
async def profile_page():
    """Serve the student profile page."""
    profile_file = frontend_path / "profile_page.html"
    if profile_file.exists():
        return FileResponse(profile_file)
    return HTMLResponse("<h1>Profile Page Not Found</h1>", status_code=404)

@app.get("/admin", response_class=HTMLResponse)
async def admin_page():
    """Serve the admin interface."""
    admin_file = frontend_path / "admin_interface.html"
    if admin_file.exists():
        return FileResponse(admin_file)
    return HTMLResponse("<h1>Admin Interface Not Found</h1>", status_code=404)

# ===== Authentication Endpoints =====

@app.post("/auth/register", status_code=status.HTTP_201_CREATED)
async def register(data: UserRegisterInput):
    """
    Register a new user.

    Args:
        data: Registration data (username, email, password, full_name)

    Returns:
        Success message with user details
    """
    try:
        db_session = get_session()
        success, error_msg, user = UserService.register_user(
            db_session,
            username=data.username,
            email=data.email,
            password=data.password,
            full_name=data.full_name,
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg,
            )

        logger.info(f"User registered: {data.username}")
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "message": "User registered successfully",
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "full_name": user.full_name,
                },
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during registration",
        )


@app.post("/auth/login", status_code=status.HTTP_200_OK)
async def login(data: UserLoginInput, request: Request):
    """
    Authenticate user and create session.

    Args:
        data: Login credentials (username, password)
        request: Incoming request (used to capture client IP)

    Returns:
        Authentication token and user details
    """
    try:
        db_session = get_session()

        # Capture client IP for the session/audit trail.
        client_ip = request.client.host if request.client else None

        success, error_msg, token, user = UserService.login_user(
            db_session,
            username=data.username,
            password=data.password,
            ip_address=client_ip,
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=error_msg,
            )

        logger.info(f"User logged in: {data.username}")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "Login successful",
                "token": token,
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "full_name": user.full_name,
                    "role": user.role,
                },
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during login",
        )


@app.post("/auth/logout", status_code=status.HTTP_200_OK)
async def logout(authorization: Optional[str] = Header(None)):
    """
    Logout user by invalidating their session token.
    Does not require a valid session (handles missing/expired tokens gracefully),
    but when a well-formed Bearer token is supplied its session row is deleted.

    Returns:
        Success message
    """
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        if token and len(token) == 64:
            try:
                db_session = get_session()
                UserService.logout_user(db_session, token)
            except Exception as e:
                logger.warning(f"Logout token invalidation failed: {str(e)}")

    # Always return success, whether or not there was an active session
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Logout successful"},
    )


# ===== User Profile Endpoints =====

class UserProfileUpdateInput(BaseModel):
    """Editable user profile fields (all optional)."""
    full_name: Optional[str] = None
    theme_preference: Optional[str] = None
    password: Optional[str] = None


def _compute_streak(history: list) -> int:
    """Count consecutive days (ending today) that have at least one quiz."""
    from datetime import datetime as _dt, date, timedelta as _td
    days = set()
    for record in history:
        created = record.get("created_at")
        if created:
            try:
                days.add(_dt.fromisoformat(created).date())
            except (ValueError, TypeError):
                continue
    streak = 0
    cursor = date.today()
    while cursor in days:
        streak += 1
        cursor -= _td(days=1)
    return streak


@app.get("/api/user/profile", status_code=status.HTTP_200_OK)
async def get_user_profile(current_user = Depends(get_current_user)):
    """Return the current user's profile details and learning stats."""
    try:
        db_session = get_session()
        stats = QuizService.get_quiz_statistics(
            db_session, user_id=current_user.id, within_retention=True
        )
        history = QuizService.get_quiz_history(
            db_session, user_id=current_user.id, limit=1000, within_retention=True
        )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "user": {
                    "id": current_user.id,
                    "username": current_user.username,
                    "email": current_user.email,
                    "full_name": current_user.full_name,
                    "role": current_user.role,
                    "theme_preference": current_user.theme_preference,
                    "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
                },
                "stats": {
                    "total_quizzes": stats.get("total_quizzes", 0),
                    "average_score": stats.get("average_score", 0),
                    "streak": _compute_streak(history),
                },
            },
        )
    except Exception as e:
        logger.error(f"Get profile error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load profile",
        )


@app.patch("/api/user/profile", status_code=status.HTTP_200_OK)
async def update_user_profile(
    data: UserProfileUpdateInput,
    current_user = Depends(get_current_user),
):
    """Update editable profile fields (full_name, theme, password)."""
    try:
        db_session = get_session()
        user = db_session.query(User).filter(User.id == current_user.id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        updated = []
        if data.full_name is not None:
            user.full_name = data.full_name.strip() or None
            updated.append("full_name")
        if data.theme_preference in ("light", "dark"):
            user.theme_preference = data.theme_preference
            updated.append("theme_preference")
        if data.password:
            if len(data.password) < 8:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Password must be at least 8 characters",
                )
            user.password_hash = hash_password(data.password)
            updated.append("password")

        db_session.commit()
        logger.info(f"Profile updated for {user.username}: {updated}")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Profile updated successfully", "updated_fields": updated},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update profile error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile",
        )


@app.delete("/api/user", status_code=status.HTTP_200_OK)
async def delete_user_account(current_user = Depends(get_current_user)):
    """Deactivate the current user's account and clear their sessions."""
    try:
        db_session = get_session()
        user = db_session.query(User).filter(User.id == current_user.id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        user.is_active = False
        db_session.query(Session).filter(Session.user_id == user.id).delete()
        db_session.commit()
        logger.info(f"Account deactivated for {user.username}")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Account deactivated"},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete account error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete account",
        )


# ===== Protected Endpoints =====

@app.post("/query", status_code=status.HTTP_200_OK)
async def process_query(
    input_data: QueryInput,
    current_user = Depends(get_current_user),
):
    """
    Process user query using AI agent with security validation.
    Requires authentication.
    Supports offline mode with automatic caching and sync.

    Performs:
    1. Connectivity check (online/offline detection)
    2. Offline mode handling (cache retrieval)
    3. Input validation (injection detection, scope checking)
    4. Agent processing
    5. Response validation
    6. Response caching
    7. Pending sync management
    8. Audit logging

    Args:
        input_data: Query input
        current_user: Authenticated user

    Returns:
        Agent response or cached response, or offline message
    """
    db_session = None
    
    try:
        db_session = get_session()
        query = input_data.query
        user_id = current_user.id
        
        # ===== PHASE 1: INPUT VALIDATION =====

        # Validate query FIRST for injection attempts and scope BEFORE accessing cache
        is_valid, validation_error = InputValidator.validate_query(query)
        
        if not is_valid:
            logger.warning(f"Invalid query from user {current_user.username}: {validation_error}")
            
            # Log as security event
            AuditLogger.log_query(
                db_session,
                user_id=user_id,
                query=query,
                is_injection_flagged=True if validation_error == "prompt injection" else False,
                is_out_of_scope=True if "out-of-scope" in validation_error.lower() else False,
                error_message=validation_error,
            )
            
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=validation_error,
            )
        
        # Extract subject from query for logging
        subject = InputValidator.extract_subject(query)

        logger.info(f"Valid query from user {current_user.username}, subject: {subject}")

        # ===== PHASE 2: CONNECTIVITY CHECK AND OFFLINE CACHE =====

        is_online, status_msg = StatusDetector.check_with_fallback()
        logger.info(f"Connectivity status for user {current_user.username}: {status_msg}")

        if not is_online:
            logger.info(f"User {current_user.username} is offline, attempting cache retrieval")

            # Try to retrieve cached response (only after validation)
            cached_response = CacheManager.get_cached_response(
                db_session,
                query=query,
                subject=subject or "unknown",
                language_code="en"
            )

            if cached_response:
                logger.info(f"Cache hit for offline user {current_user.username}")
                return JSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "data": cached_response,
                        "type": "text",
                        "metadata": {
                            "source": "offline_cache",
                            "connectivity": status_msg,
                        },
                    },
                )
            else:
                logger.warning(f"Cache miss for offline user {current_user.username}")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="You are offline and this query is not in your cache. "
                           "Please try a previous query or connect to the internet.",
                )

        # ===== PHASE 3: AGENT PROCESSING =====

        message = HumanMessage(content=query, role="user")
        agent = create_agent()

        initial_state = {"messages": [message]}
        output = await asyncio.to_thread(agent.invoke, initial_state)

        response = output["messages"][-1].content

        # Clean LaTeX notation from response
        response = clean_response(response)

        # ===== PHASE 2: RESPONSE VALIDATION =====

        # Validate response for security issues
        is_valid_response, response_error = ResponseValidator.validate_response(response, subject=subject)
        
        if not is_valid_response:
            logger.warning(f"Invalid response detected: {response_error}")
            
            # Log the security issue
            AuditLogger.log_query(
                db_session,
                user_id=user_id,
                query=query,
                subject=subject,
                tool_used="agent",
                response_length=len(response),
                error_message=f"Response validation failed: {response_error}",
            )
            
            # Return safe error message
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An error occurred while processing your query. Please try again.",
            )
        
        # Truncate response if too long
        response = ResponseValidator.truncate_response(response)
        
        # Score response quality
        quality_score = ResponseValidator.score_response_quality(response)
        
        # ===== PHASE 3: RESPONSE CACHING =====
        
        # Cache the response for offline use
        cache_success = CacheManager.cache_response(
            db_session,
            query=query,
            response=response,
            subject=subject or "unknown",
            language_code="en",
            ttl_days=7  # Cache for 7 days
        )
        
        if cache_success:
            logger.info(f"Response cached for user {current_user.username}")
        else:
            logger.warning(f"Failed to cache response for user {current_user.username}")
        
        # ===== PHASE 3: SYNC MANAGEMENT =====
        
        # Check if user has pending syncs and trigger sync if ready
        pending_syncs = SyncManager.get_pending_syncs(db_session, user_id)
        
        if pending_syncs:
            logger.info(f"User {current_user.username} has {len(pending_syncs)} pending syncs")
            # Attempt to sync all pending items
            sync_count, errors = SyncManager.sync_all_pending(db_session, user_id)
            if sync_count > 0:
                logger.info(f"Synced {sync_count} items for user {current_user.username}")
        
        # ===== PHASE 2: AUDIT LOGGING =====
        
        # Log successful query
        AuditLogger.log_query(
            db_session,
            user_id=user_id,
            query=query,
            subject=subject,
            tool_used="agent",
            response_length=len(response),
            is_injection_flagged=False,
            is_out_of_scope=False,
        )
        
        logger.info(
            f"Query processed successfully for user {current_user.username}: "
            f"subject={subject}, response_length={len(response)}, quality={quality_score:.2f}"
        )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "data": response,
                "type": "text",
                "metadata": {
                    "subject": subject,
                    "quality_score": round(quality_score, 2),
                    "source": "agent",
                    "cached": True,
                },
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        
        # Try to log the error
        try:
            if db_session and hasattr(current_user, 'id'):
                AuditLogger.log_query(
                    db_session,
                    user_id=current_user.id,
                    query=input_data.query if input_data else "unknown",
                    error_message=f"Query processing error: {str(e)}"[:500],
                )
        except Exception as log_error:
            logger.error(f"Failed to log query error: {str(log_error)}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing your query",
        )

@app.post("/api/query", status_code=status.HTTP_200_OK)
async def api_query(input_data: QueryInput):
    """
    Public API endpoint for chat interface queries.
    Does not require authentication for basic chat functionality.
    """
    try:
        db_session = get_session()
        query = input_data.query

        # Use subject/difficulty from frontend if provided, otherwise extract from query
        subject = input_data.subject or InputValidator.extract_subject(query)
        difficulty = input_data.difficulty or "medium"

        # Note: Validation is handled by the agent itself
        # Remove strict scope checking to allow the agent to handle subject validation

        # Check connectivity
        is_online, status_msg = StatusDetector.check_with_fallback()

        # Try to get cached response first
        if is_online:
            cached_response = CacheManager.get_cached_response(
                db_session,
                query=query,
                subject=subject or "unknown",
                language_code="en"
            )
            if cached_response:
                # Handle both string and dict responses
                cached_text = cached_response.get("response") if isinstance(cached_response, dict) else cached_response
                cached_text = clean_response(cached_text) if cached_text else "Unable to generate response"
                return JSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "response": cached_text,
                        "cached": True,
                    }
                )

        # Generate new response using orchestrator routing
        try:
            from src.agents.orchestrator import route_query

            response = await asyncio.to_thread(route_query, query)
            logger.debug(f"Raw agent response type: {type(response)}")
            logger.debug(f"Raw agent response: {response}")

            # Extract answer from agent response
            answer = "Unable to generate response"

            if isinstance(response, dict):
                # Check if response has 'messages' (from LangChain agent)
                if "messages" in response and isinstance(response["messages"], list):
                    # Get the last message (should be the final AI response)
                    messages = response["messages"]
                    if messages:
                        last_msg = messages[-1]
                        if hasattr(last_msg, 'content'):
                            answer = last_msg.content
                        elif isinstance(last_msg, dict) and 'content' in last_msg:
                            answer = last_msg['content']
                # Check if response has 'output' key
                elif "output" in response:
                    answer = response["output"]
                else:
                    answer = str(response)
            else:
                answer = str(response)

            # Clean response to remove LaTeX notation
            answer = clean_response(answer)

            # Cache the response if online
            if is_online:
                CacheManager.cache_response(
                    db_session,
                    query=query,
                    response=answer,
                    subject=subject or "unknown",
                    language_code="en"
                )

            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "response": answer,
                    "cached": False,
                }
            )
        except Exception as agent_error:
            logger.error(f"Agent error in API query: {str(agent_error)}", exc_info=True)
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "response": f"Error: {str(agent_error)[:200]}",
                    "cached": False,
                }
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API query error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing query: {str(e)[:100]}",
        )

# ===== Offline & Sync Endpoints =====

@app.get("/status/connectivity", status_code=status.HTTP_200_OK)
async def get_connectivity_status():
    """
    Check current connectivity status (public endpoint, no auth required).
    Used to determine if device is online/offline.

    Returns:
        Connectivity status with details
    """
    try:
        is_online, status_msg = StatusDetector.check_with_fallback()
        logger.info(f"Connectivity check: {status_msg}")
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "is_online": is_online,
                "status": status_msg,
                "timestamp": __import__('datetime').datetime.utcnow().isoformat(),
            },
        )
    
    except Exception as e:
        logger.error(f"Connectivity check error: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "is_online": False,
                "status": "Connection check failed",
                "timestamp": __import__('datetime').datetime.utcnow().isoformat(),
            },
        )


@app.get("/status/sync", status_code=status.HTTP_200_OK)
async def get_sync_status(current_user = Depends(get_current_user)):
    """
    Get synchronization status for current user.
    Shows pending offline content and sync progress.

    Args:
        current_user: Authenticated user

    Returns:
        Sync status information
    """
    try:
        db_session = get_session()
        
        sync_status = SyncManager.get_sync_status(db_session, current_user.id)
        
        logger.info(f"Sync status requested by user {current_user.username}")
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=sync_status,
        )
    
    except Exception as e:
        logger.error(f"Sync status error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve sync status",
        )


@app.post("/sync/trigger", status_code=status.HTTP_200_OK)
async def trigger_sync(current_user = Depends(get_current_user)):
    """
    Manually trigger synchronization of pending offline content.
    Called automatically during queries but can be manually invoked.

    Args:
        current_user: Authenticated user

    Returns:
        Sync results
    """
    try:
        db_session = get_session()
        
        # Check connectivity first
        is_online, status_msg = StatusDetector.check_with_fallback()
        
        if not is_online:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Device is offline. Cannot sync.",
            )
        
        # Sync all pending items
        sync_count, errors = SyncManager.sync_all_pending(db_session, current_user.id)
        
        logger.info(f"Manual sync triggered by user {current_user.username}: {sync_count} items synced")
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "synced_count": sync_count,
                "errors": errors,
                "timestamp": __import__('datetime').datetime.utcnow().isoformat(),
            },
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Sync trigger error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to trigger sync",
        )


@app.get("/cache/statistics", status_code=status.HTTP_200_OK)
async def get_cache_statistics(current_user = Depends(get_current_user)):
    """
    Get cache statistics (admin view for monitoring).
    Shows cache usage by subject and other metrics.

    Args:
        current_user: Authenticated user (admin only)

    Returns:
        Cache statistics
    """
    try:
        # Check if user is admin
        if current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can view cache statistics",
            )
        
        db_session = get_session()
        
        cache_stats = CacheManager.get_cache_statistics(db_session)
        
        logger.info(f"Cache statistics requested by admin {current_user.username}")
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=cache_stats,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Cache statistics error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve cache statistics",
        )


@app.post("/cache/cleanup", status_code=status.HTTP_200_OK)
async def cleanup_expired_cache(current_user = Depends(get_current_user)):
    """
    Manually trigger cleanup of expired cache entries.
    This runs automatically but can be manually invoked.

    Args:
        current_user: Authenticated user (admin only)

    Returns:
        Cleanup results
    """
    try:
        # Check if user is admin
        if current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can trigger cache cleanup",
            )
        
        db_session = get_session()
        
        deleted_count = CacheManager.cleanup_expired_cache(db_session)
        
        logger.info(f"Cache cleanup triggered by admin {current_user.username}: {deleted_count} entries deleted")
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "deleted_count": deleted_count,
                "timestamp": __import__('datetime').datetime.utcnow().isoformat(),
            },
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Cache cleanup error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cleanup cache",
        )


# ===== Quiz Endpoints =====

@app.post("/quiz/generate", status_code=status.HTTP_200_OK)
async def generate_quiz(
    quiz_input: QuizGenerateInput,
    current_user = Depends(get_current_user),
):
    """
    Generate a fresh quiz with specified parameters.
    Requires authentication.

    Args:
        quiz_input: Quiz configuration
        current_user: Authenticated user

    Returns:
        Generated quiz questions
    """
    try:
        logger.info(
            f"Generating {quiz_input.subject} quiz for {current_user.username}: "
            f"difficulty={quiz_input.difficulty}, count={quiz_input.question_count}"
        )
        
        # Generate quiz
        exclude_set = set(quiz_input.exclude_questions) if quiz_input.exclude_questions else set()
        logger.info(
            f"Generating quiz with {len(exclude_set)} excluded questions for subject: {quiz_input.subject}"
        )
        success, questions, error_msg = QuizGenerator.generate_quiz(
            subject=quiz_input.subject,
            difficulty=quiz_input.difficulty,
            question_count=quiz_input.question_count,
            language_code="en",
            exclude_questions=exclude_set
        )

        # Log generated question titles
        if success:
            question_titles = [q.get("question", "")[:50] + "..." for q in questions]
            logger.info(f"Generated {len(questions)} questions: {question_titles}")
        
        if not success:
            logger.warning(f"Quiz generation failed: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to generate quiz: {error_msg}",
            )
        
        logger.info(f"Quiz generated successfully: {len(questions)} questions")
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "subject": quiz_input.subject,
                "difficulty": quiz_input.difficulty,
                "topic": quiz_input.topic,
                "questions": questions,
                "question_count": len(questions),
            },
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Quiz generation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while generating the quiz",
        )


@app.post("/quiz/submit", status_code=status.HTTP_200_OK)
async def submit_quiz(
    quiz_data: QuizSubmitInput,
    current_user = Depends(get_current_user),
):
    """
    Submit quiz answers and save attempt to history.
    Requires authentication.

    Args:
        quiz_data: Quiz submission data
        current_user: Authenticated user

    Returns:
        Score and result details
    """
    try:
        db_session = get_session()
        user_id = current_user.id
        
        logger.info(f"Quiz submission from {current_user.username}: {quiz_data.subject}")
        
        # Validate answer count matches questions
        if len(quiz_data.user_answers) != len(quiz_data.questions):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Answer count does not match question count",
            )
        
        # Save quiz attempt
        success, quiz_id, error_msg = QuizService.save_quiz_attempt(
            db_session,
            user_id=user_id,
            subject=quiz_data.subject,
            topic=quiz_data.topic,
            difficulty=quiz_data.difficulty,
            questions=quiz_data.questions,
            user_answers=quiz_data.user_answers,
            time_taken_seconds=quiz_data.time_taken_seconds,
            is_offline=False,
            language_code="en"
        )
        
        if not success:
            logger.warning(f"Quiz submission failed: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save quiz attempt",
            )
        
        # Calculate score
        score, correct_count = QuizService.calculate_score(
            quiz_data.questions,
            quiz_data.user_answers
        )
        
        logger.info(
            f"Quiz submitted by {current_user.username}: "
            f"score={score}%, correct={correct_count}/{len(quiz_data.questions)}"
        )
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "quiz_id": quiz_id,
                "score": score,
                "correct_count": correct_count,
                "total_questions": len(quiz_data.questions),
                "percentage": round(score, 2),
                "message": f"Great job! You scored {score}%" if score >= 70 else f"Score: {score}%. Keep practicing!",
            },
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Quiz submission error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while submitting the quiz",
        )


@app.get("/quiz/history", status_code=status.HTTP_200_OK)
async def get_quiz_history(
    subject: Optional[str] = None,
    limit: int = 50,
    current_user = Depends(get_current_user),
):
    """
    Get user's quiz history with optional subject filtering.
    Requires authentication.

    Args:
        subject: Filter by subject (optional)
        limit: Maximum records to return
        current_user: Authenticated user

    Returns:
        List of quiz attempts
    """
    try:
        db_session = get_session()
        
        history = QuizService.get_quiz_history(
            db_session,
            user_id=current_user.id,
            subject=subject,
            limit=limit,
            within_retention=True
        )
        
        logger.info(f"Quiz history retrieved for {current_user.username}: {len(history)} records")
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "total_count": len(history),
                "subject_filter": subject,
                "quizzes": history,
            },
        )
    
    except Exception as e:
        logger.error(f"Quiz history error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve quiz history",
        )


@app.get("/quiz/statistics", status_code=status.HTTP_200_OK)
async def get_quiz_statistics(current_user = Depends(get_current_user)):
    """
    Get user's quiz performance statistics.
    Requires authentication.

    Args:
        current_user: Authenticated user

    Returns:
        Statistics including average score, breakdowns by subject/difficulty
    """
    try:
        db_session = get_session()
        
        stats = QuizService.get_quiz_statistics(
            db_session,
            user_id=current_user.id,
            within_retention=True
        )
        
        logger.info(f"Quiz statistics retrieved for {current_user.username}")
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=stats,
        )
    
    except Exception as e:
        logger.error(f"Quiz statistics error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve statistics",
        )


@app.get("/quiz/{quiz_id}", status_code=status.HTTP_200_OK)
async def get_quiz_detail(
    quiz_id: int,
    current_user = Depends(get_current_user),
):
    """
    Get detailed view of a specific quiz attempt.
    Requires authentication.

    Args:
        quiz_id: Quiz history ID
        current_user: Authenticated user

    Returns:
        Detailed quiz information with all questions and user answers
    """
    try:
        db_session = get_session()
        
        detail = QuizService.get_quiz_detail(
            db_session,
            user_id=current_user.id,
            quiz_id=quiz_id
        )
        
        if not detail:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Quiz not found",
            )
        
        logger.info(f"Quiz detail retrieved for {current_user.username}: quiz_id={quiz_id}")
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=detail,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Quiz detail error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve quiz details",
        )


# ===== NEW: Detailed Quiz Tracking Endpoints =====

@app.post("/quiz/attempt/start", status_code=status.HTTP_201_CREATED)
async def start_quiz_attempt(
    quiz_input: QuizAttemptStartInput,
    current_user = Depends(get_current_user),
):
    """
    Start a new quiz attempt and return questions.
    Requires authentication.

    Args:
        quiz_input: Quiz configuration
        current_user: Authenticated user

    Returns:
        Quiz attempt ID and questions
    """
    try:
        db_session = get_session()

        # Get or create difficulty profile
        profile = DifficultyCalibrationService.get_or_create_profile(
            db_session,
            current_user.id,
            quiz_input.subject
        )

        # Use recommended difficulty if not specified
        difficulty = quiz_input.difficulty or profile.current_difficulty

        # Create quiz attempt record
        attempt = QuizAttemptService.create_quiz_attempt(
            db_session,
            current_user.id,
            quiz_input.subject,
            difficulty,
            quiz_input.question_count
        )

        # Generate questions
        success, questions, error = QuizGenerator.generate_quiz(
            subject=quiz_input.subject,
            difficulty=difficulty,
            question_count=quiz_input.question_count
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to generate quiz: {error}"
            )

        logger.info(f"Quiz attempt {attempt.id} started for {current_user.username}")

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "attempt_id": attempt.id,
                "subject": quiz_input.subject,
                "difficulty": difficulty,
                "question_count": len(questions),
                "questions": questions,
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Quiz attempt start error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start quiz attempt"
        )


@app.post("/quiz/attempt/{attempt_id}/answer", status_code=status.HTTP_200_OK)
async def submit_question_answer(
    attempt_id: int,
    answer_input: QuestionAnswerInput,
    current_user = Depends(get_current_user),
):
    """
    Submit an answer to a question during quiz.
    Requires authentication.

    Args:
        attempt_id: Quiz attempt ID
        answer_input: Answer data
        current_user: Authenticated user

    Returns:
        Score for this answer and feedback
    """
    try:
        db_session = get_session()

        # Verify quiz attempt belongs to user
        attempt = db_session.query(QuizAttempt).filter(
            QuizAttempt.id == attempt_id,
            QuizAttempt.user_id == current_user.id
        ).first()

        if not attempt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Quiz attempt not found"
            )

        if attempt.status != "in_progress":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Quiz attempt is not in progress"
            )

        # Grade against the supplied correct answer when provided; otherwise record
        # the answer without auto-scoring (the primary scored flow is /quiz/submit).
        if answer_input.correct_answer is not None:
            is_correct = (
                answer_input.student_answer.strip().lower()
                == answer_input.correct_answer.strip().lower()
            )
            correct_answer_text = answer_input.correct_answer
            feedback = "Correct!" if is_correct else f"Incorrect. Expected: {answer_input.correct_answer}"
        else:
            is_correct = False
            correct_answer_text = "(not provided)"
            feedback = "Answer recorded (not auto-graded; use /quiz/submit for scoring)."
        score_earned = 1.0 if is_correct else 0.0

        # Record the answer
        student_answer = QuizAttemptService.record_answer(
            db_session,
            attempt_id,
            None,  # question_id (would be set if using PaperQuestion)
            f"Question {answer_input.question_number}",
            answer_input.student_answer,
            correct_answer_text,
            is_correct,
            score_earned,
            1.0,  # marks_total
            feedback
        )

        logger.info(f"Answer recorded for quiz attempt {attempt_id}: Q{answer_input.question_number}")

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "answer_id": student_answer.id,
                "is_correct": is_correct,
                "score": score_earned,
                "feedback": feedback,
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Answer submission error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit answer"
        )


@app.post("/quiz/attempt/{attempt_id}/complete", status_code=status.HTTP_200_OK)
async def complete_quiz_attempt(
    attempt_id: int,
    complete_input: QuizAttemptCompleteInput,
    current_user = Depends(get_current_user),
):
    """
    Complete a quiz attempt and calculate final score.
    Triggers difficulty calibration.
    Requires authentication.

    Args:
        attempt_id: Quiz attempt ID
        complete_input: Completion data with time taken
        current_user: Authenticated user

    Returns:
        Final score and difficulty adjustment
    """
    try:
        db_session = get_session()

        # Verify quiz attempt belongs to user
        attempt = db_session.query(QuizAttempt).filter(
            QuizAttempt.id == attempt_id,
            QuizAttempt.user_id == current_user.id
        ).first()

        if not attempt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Quiz attempt not found"
            )

        # Complete the quiz
        completed_attempt = QuizAttemptService.complete_quiz_attempt(
            db_session,
            attempt_id,
            complete_input.total_time_seconds
        )

        # Get updated difficulty profile
        profile = DifficultyCalibrationService.get_or_create_profile(
            db_session,
            current_user.id,
            completed_attempt.subject
        )

        logger.info(f"Quiz attempt {attempt_id} completed: score={completed_attempt.score_percentage:.1f}%, difficulty={profile.current_difficulty}")

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "attempt_id": attempt_id,
                "score": completed_attempt.score_percentage,
                "current_difficulty": profile.current_difficulty,
                "next_recommended_difficulty": profile.current_difficulty,
                "accuracy_rate": profile.accuracy_rate,
                "improvement_message": f"Great job! Keep it up!" if completed_attempt.score_percentage >= 70 else "Keep practicing!",
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Quiz completion error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete quiz"
        )


@app.get("/quiz/performance", status_code=status.HTTP_200_OK)
async def get_quiz_performance(
    current_user = Depends(get_current_user),
):
    """
    Get user's performance summary across all subjects.
    Requires authentication.

    Args:
        current_user: Authenticated user

    Returns:
        Performance metrics by subject
    """
    try:
        db_session = get_session()

        performance = QuizAttemptService.get_user_performance_summary(
            db_session,
            current_user.id
        )

        logger.info(f"Performance summary retrieved for {current_user.username}")

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=performance
        )

    except Exception as e:
        logger.error(f"Performance retrieval error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve performance data"
        )


@app.get("/quiz/recommended-difficulty/{subject}", status_code=status.HTTP_200_OK)
async def get_recommended_difficulty(
    subject: str,
    current_user = Depends(get_current_user),
):
    """
    Get recommended difficulty for next quiz based on performance.
    Requires authentication.

    Args:
        subject: Subject name
        current_user: Authenticated user

    Returns:
        Recommended difficulty and reasoning
    """
    try:
        db_session = get_session()

        profile = DifficultyCalibrationService.get_or_create_profile(
            db_session,
            current_user.id,
            subject
        )

        reasoning = []
        if profile.quizzes_completed == 0:
            reasoning.append("Starting at easy level")
        elif profile.accuracy_rate >= 80:
            reasoning.append(f"Excellent performance ({profile.accuracy_rate:.0f}% accuracy) - ready for harder challenges!")
        elif profile.accuracy_rate < 50:
            reasoning.append(f"Difficulty may need adjustment ({profile.accuracy_rate:.0f}% accuracy)")
        else:
            reasoning.append(f"Solid performance ({profile.accuracy_rate:.0f}% accuracy) - maintain current level")

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "subject": subject,
                "recommended_difficulty": profile.current_difficulty,
                "current_accuracy": profile.accuracy_rate,
                "quizzes_completed": profile.quizzes_completed,
                "reasoning": reasoning,
            }
        )

    except Exception as e:
        logger.error(f"Recommended difficulty error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get recommended difficulty"
        )


# ===== Essay Evaluation Endpoints =====

@app.post("/quiz/evaluate-essay", status_code=status.HTTP_200_OK)
async def evaluate_essay_answer(
    evaluation_input: EssayEvaluationInput,
    current_user = Depends(get_current_user),
):
    """
    Evaluate an essay-type answer using Claude AI.
    Provides detailed feedback and scoring.
    Requires authentication.

    Args:
        evaluation_input: Essay and marking scheme details
        current_user: Authenticated user

    Returns:
        Score, feedback, and detailed rubric analysis
    """
    try:
        score, feedback, rubric = EssayEvaluationService.evaluate_essay(
            student_essay=evaluation_input.student_essay,
            question_text=evaluation_input.question_text,
            model_answer=evaluation_input.model_answer,
            marking_scheme=evaluation_input.marking_scheme,
            marks_total=evaluation_input.marks_total,
            subject=evaluation_input.subject,
            difficulty=evaluation_input.difficulty
        )

        logger.info(f"Essay evaluated for {current_user.username}: {score}/{evaluation_input.marks_total}")

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "score": score,
                "marks_total": evaluation_input.marks_total,
                "percentage": round((score / evaluation_input.marks_total * 100), 1),
                "feedback": feedback,
                "rubric": rubric,
            }
        )

    except Exception as e:
        logger.error(f"Essay evaluation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to evaluate essay"
        )


# ===== Practice Plan Endpoints =====

@app.get("/quiz/practice-plan", status_code=status.HTTP_200_OK)
async def get_practice_plan(
    subject: str,
    weeks_ahead: int = 4,
    current_user = Depends(get_current_user),
):
    """
    Get personalized practice plan based on performance.
    Requires authentication.

    Args:
        subject: Subject (Maths, English, etc.)
        weeks_ahead: Number of weeks to plan for
        current_user: Authenticated user

    Returns:
        Comprehensive practice plan with priorities and resources
    """
    try:
        db_session = get_session()

        plan = PracticePlanService.generate_practice_plan(
            db_session,
            current_user.id,
            subject,
            weeks_ahead
        )

        logger.info(f"Practice plan generated for {current_user.username} in {subject}")

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=plan
        )

    except Exception as e:
        logger.error(f"Practice plan error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate practice plan"
        )


@app.get("/quiz/immediate-actions", status_code=status.HTTP_200_OK)
async def get_immediate_actions(
    subject: str,
    current_user = Depends(get_current_user),
):
    """
    Get immediate action items for today/this week.
    Prioritized by urgency and weak areas.
    Requires authentication.

    Args:
        subject: Subject
        current_user: Authenticated user

    Returns:
        List of prioritized immediate actions
    """
    try:
        db_session = get_session()

        actions = PracticePlanService.get_immediate_actions(
            db_session,
            current_user.id,
            subject
        )

        logger.info(f"Immediate actions retrieved for {current_user.username}")

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "subject": subject,
                "actions": actions,
                "total_actions": len(actions),
            }
        )

    except Exception as e:
        logger.error(f"Immediate actions error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve actions"
        )


# ===== Spaced Repetition Endpoints =====

@app.get("/quiz/topics-due-for-review", status_code=status.HTTP_200_OK)
async def get_topics_due_for_review(
    subject: str,
    current_user = Depends(get_current_user),
):
    """
    Get topics that are due for review using spaced repetition algorithm.
    Requires authentication.

    Args:
        subject: Subject
        current_user: Authenticated user

    Returns:
        List of topics sorted by urgency
    """
    try:
        db_session = get_session()

        topics = SpacedRepetitionService.get_topics_due_for_review(
            db_session,
            current_user.id,
            subject
        )

        logger.info(f"Topics due for review retrieved for {current_user.username}")

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "subject": subject,
                "topics_due": topics,
                "total_due": len(topics),
            }
        )

    except Exception as e:
        logger.error(f"Topics due for review error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve topics"
        )


@app.get("/quiz/study-schedule", status_code=status.HTTP_200_OK)
async def get_study_schedule(
    subject: str,
    days_ahead: int = 7,
    current_user = Depends(get_current_user),
):
    """
    Get recommended study schedule for next N days.
    Requires authentication.

    Args:
        subject: Subject
        days_ahead: Days to plan for
        current_user: Authenticated user

    Returns:
        Daily study schedule with recommended topics
    """
    try:
        db_session = get_session()

        schedule = SpacedRepetitionService.get_study_schedule(
            db_session,
            current_user.id,
            subject,
            days_ahead
        )

        logger.info(f"Study schedule retrieved for {current_user.username}")

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "subject": subject,
                "days_ahead": days_ahead,
                "schedule": schedule,
            }
        )

    except Exception as e:
        logger.error(f"Study schedule error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve schedule"
        )


@app.get("/quiz/topic-performance", status_code=status.HTTP_200_OK)
async def get_topic_performance(
    subject: str,
    current_user = Depends(get_current_user),
):
    """
    Get detailed performance breakdown by topic.
    Requires authentication.

    Args:
        subject: Subject
        current_user: Authenticated user

    Returns:
        Performance metrics for each topic
    """
    try:
        db_session = get_session()

        performance = TopicPerformanceService.get_topic_performance(
            db_session,
            current_user.id,
            subject
        )

        logger.info(f"Topic performance retrieved for {current_user.username}")

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "subject": subject,
                "topics": performance,
            }
        )

    except Exception as e:
        logger.error(f"Topic performance error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve topic performance"
        )


@app.get("/quiz/time-to-proficiency", status_code=status.HTTP_200_OK)
async def get_time_to_proficiency(
    subject: str,
    topic: str,
    current_accuracy: float,
    target_accuracy: float = 85.0,
    hours_per_week: float = 5.0,
    current_user = Depends(get_current_user),
):
    """
    Estimate time needed to reach target proficiency.
    Requires authentication.

    Args:
        subject: Subject
        topic: Topic name
        current_accuracy: Current accuracy (0-100)
        target_accuracy: Target accuracy (0-100)
        hours_per_week: Study hours available per week
        current_user: Authenticated user

    Returns:
        Time estimate and milestone breakdown
    """
    try:
        estimate = PracticePlanService.estimate_time_to_proficiency(
            current_accuracy,
            target_accuracy,
            hours_per_week
        )

        logger.info(f"Proficiency estimate for {current_user.username}: {estimate['weeks_required']} weeks")

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "subject": subject,
                "topic": topic,
                "current_accuracy": current_accuracy,
                "target_accuracy": target_accuracy,
                **estimate,
            }
        )

    except Exception as e:
        logger.error(f"Proficiency estimate error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to estimate proficiency"
        )


@app.post("/admin/quiz/cleanup", status_code=status.HTTP_200_OK)
async def cleanup_old_quizzes(current_user = Depends(get_current_user)):
    """
    Manually trigger cleanup of quizzes older than 60-day retention.
    Admin only. Runs automatically but can be manually invoked.

    Args:
        current_user: Authenticated user (admin only)

    Returns:
        Cleanup results
    """
    try:
        # Check if user is admin
        if current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can trigger quiz cleanup",
            )
        
        db_session = get_session()
        
        deleted_count = QuizService.cleanup_old_quizzes(db_session)
        
        logger.info(f"Quiz cleanup triggered by admin {current_user.username}: {deleted_count} entries deleted")
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "deleted_count": deleted_count,
                "retention_days": QuizService.RETENTION_DAYS,
                "timestamp": __import__('datetime').datetime.utcnow().isoformat(),
            },
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Quiz cleanup error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cleanup quizzes",
        )


# ===== PHASE 5: Admin Endpoints =====

@app.get("/admin/users", status_code=status.HTTP_200_OK)
async def get_all_users(
    current_user: object = Depends(get_current_user),
    limit: int = 100,
    offset: int = 0,
):
    """
    Get all users with statistics (Admin only).
    
    Requires admin role.
    
    Args:
        current_user: Current authenticated user
        limit: Max records
        offset: Pagination offset
        
    Returns:
        List of users with stats
    """
    try:
        db_session = get_session()
        
        # Check admin access
        is_admin, msg = AdminService.verify_admin_access(current_user.id, db_session)
        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required",
            )
        
        success, users, error = AdminService.get_all_users(
            db_session, limit=limit, offset=offset
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error,
            )
        
        logger.info(f"Admin {current_user.username} retrieved user list")
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "users": users,
                "count": len(users),
                "timestamp": __import__('datetime').datetime.utcnow().isoformat(),
            },
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get users error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve users",
        )


@app.get("/admin/user/{user_id}", status_code=status.HTTP_200_OK)
async def get_user_detail(
    user_id: int,
    current_user: object = Depends(get_current_user),
):
    """
    Get detailed user information with activity history (Admin only).
    
    Args:
        user_id: User ID to retrieve
        current_user: Current authenticated user
        
    Returns:
        Detailed user information
    """
    try:
        db_session = get_session()
        
        # Check admin access
        is_admin, msg = AdminService.verify_admin_access(current_user.id, db_session)
        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required",
            )
        
        success, user_detail, error = AdminService.get_user_detail(db_session, user_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error,
            )
        
        logger.info(f"Admin {current_user.username} viewed user {user_id} details")
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=user_detail,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get user detail error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user detail",
        )


@app.post("/admin/user/{user_id}/action", status_code=status.HTTP_200_OK)
async def admin_user_action(
    user_id: int,
    action_input: AdminUserActionInput,
    current_user: object = Depends(get_current_user),
):
    """
    Perform admin action on user (enable, disable, reset password, deactivate).
    
    Args:
        user_id: User ID
        action_input: Action details
        current_user: Current authenticated user
        
    Returns:
        Action result
    """
    try:
        db_session = get_session()
        
        # Check admin access
        is_admin, msg = AdminService.verify_admin_access(current_user.id, db_session)
        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required",
            )
        
        # Validate action
        valid_actions = ["enable", "disable", "reset_password", "deactivate"]
        if action_input.action not in valid_actions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid action. Must be one of: {', '.join(valid_actions)}",
            )
        
        success, message = AdminService.perform_user_action(
            db_session, user_id, action_input.action
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=message,
            )
        
        logger.warning(f"Admin {current_user.username} performed action '{action_input.action}' on user {user_id}: {action_input.reason}")
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "message": message,
                "action": action_input.action,
                "user_id": user_id,
            },
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin user action error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to perform user action",
        )


@app.get("/admin/queries", status_code=status.HTTP_200_OK)
async def get_monitored_queries(
    current_user: object = Depends(get_current_user),
    user_id: Optional[int] = None,
    subject: Optional[str] = None,
    has_injection: Optional[bool] = None,
    limit: int = 100,
):
    """
    Get monitored queries with filtering (Admin only).
    
    Args:
        current_user: Current authenticated user
        user_id: Filter by user ID (optional)
        subject: Filter by subject (optional)
        has_injection: Filter by injection detection (optional)
        limit: Max records
        
    Returns:
        List of monitored queries
    """
    try:
        db_session = get_session()
        
        # Check admin access
        is_admin, msg = AdminService.verify_admin_access(current_user.id, db_session)
        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required",
            )
        
        success, queries, error = AdminService.get_monitored_queries(
            db_session,
            user_id=user_id,
            subject=subject,
            has_injection_flag=has_injection,
            limit=limit,
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error,
            )
        
        logger.info(f"Admin {current_user.username} retrieved monitored queries")
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "queries": queries,
                "count": len(queries),
                "filters": {
                    "user_id": user_id,
                    "subject": subject,
                    "has_injection": has_injection,
                },
            },
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get monitored queries error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve queries",
        )


@app.get("/admin/security-alerts", status_code=status.HTTP_200_OK)
async def get_security_alerts(
    current_user: object = Depends(get_current_user),
    limit: int = 50,
):
    """
    Get security alerts (injection attempts, scope violations, etc.) (Admin only).
    
    Args:
        current_user: Current authenticated user
        limit: Max alerts
        
    Returns:
        List of security alerts
    """
    try:
        db_session = get_session()
        
        # Check admin access
        is_admin, msg = AdminService.verify_admin_access(current_user.id, db_session)
        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required",
            )
        
        success, alerts, error = AdminService.get_security_alerts(
            db_session, limit=limit
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error,
            )
        
        logger.info(f"Admin {current_user.username} retrieved security alerts")
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "alerts": alerts,
                "count": len(alerts),
                "critical_count": sum(1 for a in alerts if a["severity"] == "high"),
                "timestamp": __import__('datetime').datetime.utcnow().isoformat(),
            },
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get security alerts error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve security alerts",
        )


@app.get("/admin/dashboard/stats", status_code=status.HTTP_200_OK)
async def get_dashboard_statistics(
    current_user: object = Depends(get_current_user),
):
    """
    Get overall system dashboard statistics (Admin only).
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        System statistics
    """
    try:
        db_session = get_session()
        
        # Check admin access
        is_admin, msg = AdminService.verify_admin_access(current_user.id, db_session)
        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required",
            )
        
        success, stats, error = AdminService.get_dashboard_statistics(db_session)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error,
            )
        
        logger.info(f"Admin {current_user.username} viewed dashboard statistics")
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=stats,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get dashboard stats error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve dashboard statistics",
        )


@app.get("/admin/dashboard/usage", status_code=status.HTTP_200_OK)
async def get_usage_statistics(
    current_user: object = Depends(get_current_user),
):
    """
    Get system usage statistics (storage, cache, database) (Admin only).
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Usage statistics
    """
    try:
        db_session = get_session()
        
        # Check admin access
        is_admin, msg = AdminService.verify_admin_access(current_user.id, db_session)
        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required",
            )
        
        success, usage, error = AdminService.get_usage_statistics(db_session)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error,
            )
        
        logger.info(f"Admin {current_user.username} viewed usage statistics")
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=usage,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get usage stats error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve usage statistics",
        )


@app.post("/admin/cleanup", status_code=status.HTTP_200_OK)
async def admin_cleanup(
    cleanup_input: AdminCleanupInput,
    current_user: object = Depends(get_current_user),
):
    """
    Perform admin cleanup of cache or audit logs.
    
    Args:
        cleanup_input: Cleanup request
        current_user: Current authenticated user
        
    Returns:
        Cleanup result
    """
    try:
        db_session = get_session()
        
        # Check admin access
        is_admin, msg = AdminService.verify_admin_access(current_user.id, db_session)
        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required",
            )
        
        if cleanup_input.resource_type == "cache":
            success, stats, error = AdminService.cleanup_cache(
                db_session, older_than_days=cleanup_input.older_than_days
            )
        elif cleanup_input.resource_type == "audit_logs":
            success, stats, error = AdminService.cleanup_audit_logs(
                db_session, older_than_days=cleanup_input.older_than_days
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid resource_type. Must be 'cache' or 'audit_logs'",
            )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error,
            )
        
        logger.warning(f"Admin {current_user.username} performed cleanup: resource={cleanup_input.resource_type}, days={cleanup_input.older_than_days}")
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "resource_type": cleanup_input.resource_type,
                "statistics": stats,
            },
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin cleanup error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to perform cleanup",
        )


@app.post("/admin/export-data", status_code=status.HTTP_200_OK)
async def export_user_data(
    export_input: AdminDataExportInput,
    current_user: object = Depends(get_current_user),
):
    """
    Export user data for compliance (GDPR, etc.) (Admin only).
    
    Args:
        export_input: Export request
        current_user: Current authenticated user
        
    Returns:
        Exported user data
    """
    try:
        db_session = get_session()
        
        # Check admin access
        is_admin, msg = AdminService.verify_admin_access(current_user.id, db_session)
        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required",
            )
        
        success, export_data, error = AdminService.export_user_data(
            db_session, export_input.user_id, format=export_input.format
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error,
            )
        
        logger.warning(f"Admin {current_user.username} exported data for user {export_input.user_id} in {export_input.format} format")
        
        content_type = "application/json" if export_input.format == "json" else "text/csv"
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "format": export_input.format,
                "user_id": export_input.user_id,
                "data": export_data,
                "timestamp": __import__('datetime').datetime.utcnow().isoformat(),
            },
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Export user data error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export user data",
        )


@app.post("/notifications/send", status_code=status.HTTP_200_OK)
async def send_notification(
    notification_input: SendNotificationInput,
    current_user: object = Depends(get_current_user),
):
    """
    Send notification to user about due topics.

    Args:
        notification_input: Notification request details
        current_user: Current authenticated user

    Returns:
        Notification status
    """
    try:
        db_session = get_session()
        from src.services.notification_service import NotificationService

        # Verify user can only send to themselves (unless admin)
        is_admin = getattr(current_user, "is_admin", False)
        if not is_admin and current_user.id != notification_input.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot send notifications to other users",
            )

        # Initialize notification service
        notification_service = NotificationService(
            smtp_host=os.getenv("SMTP_HOST"),
            smtp_port=int(os.getenv("SMTP_PORT", 587)),
            sender_email=os.getenv("SENDER_EMAIL"),
            sender_password=os.getenv("SENDER_PASSWORD"),
            twilio_account_sid=os.getenv("TWILIO_ACCOUNT_SID"),
            twilio_auth_token=os.getenv("TWILIO_AUTH_TOKEN"),
            twilio_phone_number=os.getenv("TWILIO_PHONE_NUMBER"),
        )

        # Get user details
        user = db_session.query(User).filter(User.id == notification_input.user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        # Send notification
        results = notification_service.send_due_topics_notification(
            db_session,
            user_id=notification_input.user_id,
            recipient_email=user.email,
            phone_number=getattr(user, "phone_number", None),
            student_name=user.username,
            subject=notification_input.subject,
        )

        logger.info(f"Notification sent to user {notification_input.user_id}: {results}")

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": results.get("email") or results.get("sms"),
                "email_sent": results.get("email", False),
                "sms_sent": results.get("sms", False),
                "due_topics_count": results.get("due_topics_count", 0),
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Send notification error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send notification",
        )


@app.get("/notifications/preferences", status_code=status.HTTP_200_OK)
async def get_notification_preferences(
    current_user: object = Depends(get_current_user),
):
    """
    Get user's notification preferences.

    Args:
        current_user: Current authenticated user

    Returns:
        Notification preferences
    """
    try:
        db_session = get_session()
        from src.services.notification_service import NotificationPreferences

        preferences = NotificationPreferences.get_preferences(db_session, current_user.id)

        logger.info(f"Retrieved notification preferences for user {current_user.id}")

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=preferences,
        )

    except Exception as e:
        logger.error(f"Get preferences error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve preferences",
        )


@app.post("/notifications/preferences", status_code=status.HTTP_200_OK)
async def update_notification_preferences(
    preference_input: NotificationPreferenceInput,
    current_user: object = Depends(get_current_user),
):
    """
    Update user's notification preferences.

    Args:
        preference_input: Updated preferences
        current_user: Current authenticated user

    Returns:
        Update status
    """
    try:
        db_session = get_session()
        from src.services.notification_service import NotificationPreferences

        # Build preferences dict (only update provided values)
        preferences = {
            k: v for k, v in preference_input.dict().items()
            if v is not None
        }

        success = NotificationPreferences.update_preferences(
            db_session,
            current_user.id,
            preferences
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update preferences",
            )

        logger.info(f"Updated preferences for user {current_user.id}: {preferences}")

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "message": "Preferences updated successfully",
                "updated_fields": list(preferences.keys()),
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update preferences error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update preferences",
        )


@app.post("/notifications/weekly-summary", status_code=status.HTTP_200_OK)
async def send_weekly_summary(
    current_user: object = Depends(get_current_user),
):
    """
    Send weekly performance summary email to user.

    Args:
        current_user: Current authenticated user

    Returns:
        Email send status
    """
    try:
        db_session = get_session()
        from src.services.notification_service import NotificationService
        from src.services.spaced_repetition_service import TopicPerformanceService

        # Initialize notification service
        notification_service = NotificationService(
            smtp_host=os.getenv("SMTP_HOST"),
            smtp_port=int(os.getenv("SMTP_PORT", 587)),
            sender_email=os.getenv("SENDER_EMAIL"),
            sender_password=os.getenv("SENDER_PASSWORD"),
        )

        # Get user details
        user = db_session.query(User).filter(User.id == current_user.id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        # Get performance data
        quizzes = db_session.query(QuizAttempt).filter(
            QuizAttempt.user_id == current_user.id
        ).order_by(QuizAttempt.completed_at.desc()).limit(10).all()

        # Aggregate by subject
        subjects = {}
        for quiz in quizzes:
            subject = quiz.subject
            if subject not in subjects:
                subjects[subject] = {
                    "average_score": 0,
                    "quizzes_completed": 0,
                    "scores": []
                }
            subjects[subject]["scores"].append(quiz.score_percentage)
            subjects[subject]["quizzes_completed"] += 1

        # Calculate averages
        for subject in subjects:
            subjects[subject]["average_score"] = sum(subjects[subject]["scores"]) / len(subjects[subject]["scores"])

        overall_accuracy = sum(s["average_score"] for s in subjects.values()) / len(subjects) if subjects else 0

        performance_data = {
            "subjects": subjects,
            "overall_accuracy": overall_accuracy,
            "total_time_minutes": sum(q.time_taken_seconds for q in quizzes) // 60 if quizzes else 0,
        }

        # Send email
        success = notification_service.send_performance_summary(
            user.email,
            user.username,
            performance_data
        )

        logger.info(f"Weekly summary sent to user {current_user.id}: {success}")

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": success,
                "message": "Weekly summary email sent" if success else "Failed to send email",
                "summary": performance_data,
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Send weekly summary error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send weekly summary",
        )


@app.get("/notifications/history", status_code=status.HTTP_200_OK)
async def get_notification_history(
    current_user: object = Depends(get_current_user),
    limit: int = 50,
    offset: int = 0,
):
    """
    Get user's notification history.

    Args:
        current_user: Current authenticated user
        limit: Number of records to return
        offset: Number of records to skip

    Returns:
        List of notifications with metadata
    """
    try:
        db_session = get_session()

        # Get notifications
        notifications = db_session.query(NotificationHistory).filter(
            NotificationHistory.user_id == current_user.id
        ).order_by(
            NotificationHistory.created_at.desc()
        ).offset(offset).limit(limit).all()

        # Format response
        history = [
            {
                "id": n.id,
                "type": n.notification_type,
                "recipient": n.recipient,
                "subject": n.subject,
                "status": n.status,
                "topic_count": n.topic_count,
                "sent_at": n.created_at.isoformat() if n.created_at else None,
                "delivered_at": n.delivery_timestamp.isoformat() if n.delivery_timestamp else None,
                "read": n.read_at is not None,
            }
            for n in notifications
        ]

        # Get total count
        total = db_session.query(NotificationHistory).filter(
            NotificationHistory.user_id == current_user.id
        ).count()

        logger.info(f"Retrieved notification history for user {current_user.id}")

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "notifications": history,
                "total": total,
                "limit": limit,
                "offset": offset,
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get notification history error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve notification history",
        )


@app.post("/notifications/mark-read/{notification_id}", status_code=status.HTTP_200_OK)
async def mark_notification_read(
    notification_id: int,
    current_user: object = Depends(get_current_user),
):
    """
    Mark notification as read.

    Args:
        notification_id: ID of notification to mark as read
        current_user: Current authenticated user

    Returns:
        Updated notification status
    """
    try:
        db_session = get_session()

        # Get notification
        notification = db_session.query(NotificationHistory).filter(
            NotificationHistory.id == notification_id,
            NotificationHistory.user_id == current_user.id
        ).first()

        if not notification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found",
            )

        # Mark as read
        from datetime import datetime
        notification.read_at = datetime.utcnow()
        db_session.commit()

        logger.info(f"Marked notification {notification_id} as read for user {current_user.id}")

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "notification_id": notification_id,
                "read_at": notification.read_at.isoformat(),
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Mark notification read error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update notification",
        )


@app.get("/notifications/stats", status_code=status.HTTP_200_OK)
async def get_notification_stats(
    current_user: object = Depends(get_current_user),
):
    """
    Get notification statistics for user.

    Args:
        current_user: Current authenticated user

    Returns:
        Notification statistics
    """
    try:
        db_session = get_session()

        # Get stats
        total = db_session.query(NotificationHistory).filter(
            NotificationHistory.user_id == current_user.id
        ).count()

        unread = db_session.query(NotificationHistory).filter(
            NotificationHistory.user_id == current_user.id,
            NotificationHistory.read_at == None
        ).count()

        by_type = {}
        notifications = db_session.query(NotificationHistory).filter(
            NotificationHistory.user_id == current_user.id
        ).all()

        for n in notifications:
            if n.notification_type not in by_type:
                by_type[n.notification_type] = 0
            by_type[n.notification_type] += 1

        by_status = {}
        for n in notifications:
            if n.status not in by_status:
                by_status[n.status] = 0
            by_status[n.status] += 1

        logger.info(f"Retrieved notification stats for user {current_user.id}")

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "total": total,
                "unread": unread,
                "by_type": by_type,
                "by_status": by_status,
            },
        )

    except Exception as e:
        logger.error(f"Get notification stats error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve notification statistics",
        )


@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """
    Health check endpoint (public).

    Returns:
        Health status
    """
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": "healthy"},
    )

