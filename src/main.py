"""
FastAPI main application with authentication and agent integration.
Follows SonarQube standards for security S2053, S2629, S4502.
"""

import asyncio
import logging
import sys
import os
import time
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, status, Depends, HTTPException, Header, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel, EmailStr, field_validator
from langchain_core.messages import HumanMessage

from src.agents.orchestrator import create_agent
from src.database import get_db_manager, init_database, get_session
from src.auth import UserService
from src.security import InputValidator, ResponseValidator, AuditLogger
from src.offline import CacheManager, SyncManager, StatusDetector
from src.quiz import QuizGenerator, QuizService
from src.admin import AdminService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

    yield

    # Shutdown
    logger.info("Application shutting down...")
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
    allow_origins=["http://localhost:8501", "http://localhost:8000"],  # Streamlit ports
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# Add logging middleware
app.add_middleware(LoggingMiddleware)


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
async def login(data: UserLoginInput):
    """
    Authenticate user and create session.

    Args:
        data: Login credentials (username, password)

    Returns:
        Authentication token and user details
    """
    try:
        db_session = get_session()
        
        # TODO: Get client IP from request
        client_ip = None

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
async def logout(current_user = Depends(get_current_user), token: str = Depends(get_auth_token)):
    """
    Logout user by invalidating their session token.

    Args:
        current_user: Authenticated user
        token: Session token

    Returns:
        Success message
    """
    try:
        db_session = get_session()
        UserService.logout_user(db_session, token)

        logger.info(f"User logged out: {current_user.username}")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Logout successful"},
        )

    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during logout",
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
        success, questions, error_msg = QuizGenerator.generate_quiz(
            subject=quiz_input.subject,
            difficulty=quiz_input.difficulty,
            question_count=quiz_input.question_count,
            language_code="en",
            exclude_questions=exclude_set
        )
        
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

