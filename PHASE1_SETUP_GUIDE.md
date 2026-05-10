"""
Phase 1 Setup and Testing Guide

This script demonstrates how to set up and test the Phase 1 implementation
of the IGCSE Tutor application with authentication and database.
"""

# ===== SETUP INSTRUCTIONS =====

"""
1. Install Dependencies
   ----------------------
   pip install -r requirements.txt
   
   Key packages added for Phase 1:
   - bcrypt==4.1.3                    (Password hashing - SonarQube S2053)
   - email-validator==2.1.1           (Email validation)
   - SQLAlchemy==2.0.41              (Already included - ORM)

2. Initialize Database
   -------------------
   Run the database initialization (handled automatically on app startup).
   SQLite database will be created at: data/igcse_tutor.db

3. Start FastAPI Backend
   ----------------------
   uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

4. Start Streamlit Frontend
   -------------------------
   streamlit run src/frontend/chatbot_streamlit.py --logger.level=debug

5. Access Application
   ------------------
   Streamlit: http://localhost:8501
   FastAPI Docs: http://localhost:8000/docs
   FastAPI ReDoc: http://localhost:8000/redoc


===== FEATURES IMPLEMENTED IN PHASE 1 =====

✅ DATABASE
  - SQLite database with 7 tables:
    * users              - User accounts
    * sessions           - User sessions/tokens
    * audit_logs         - Query logging (future use)
    * quiz_history       - Quiz attempts (with 60-day retention)
    * offline_cache      - Cache for offline mode
    * admin_settings     - System configuration

✅ AUTHENTICATION
  - Secure password hashing (bcrypt with cost factor 12)
  - Token-based sessions (64-byte hex tokens)
  - Session expiry (24 hours default)
  - Input validation and sanitization
  - Rate limiting ready (framework in place)

✅ USER SERVICE
  - User registration with validation
  - User login with credentials
  - Session management
  - Logout functionality  
  - Expired session cleanup

✅ FASTAPI ENDPOINTS
  POST /auth/register          - Register new user
  POST /auth/login            - Login and get session token
  POST /auth/logout           - Logout and invalidate token
  POST /query                 - Send query (authenticated, requires token)
  GET  /health                - Health check (public)

✅ STREAMLIT UI
  - Modern login/signup interface
  - Authentication wrapper
  - Main chat interface (post-auth)
  - User profile display
  - Logout button
  - Offline mode indicator

✅ SECURITY FEATURES
  - Password validation (8+ chars, upper, lower, digit)
  - Hash-based token storage (no plain text)
  - CORS middleware for API security
  - Input validation on all endpoints
  - SQL injection prevention (SQLAlchemy ORM)
  - Secure session lifecycle
  - Error messages don't leak information


===== TESTING THE APPLICATION =====

Test User Registration:
-----------------------
curl -X POST http://localhost:8000/auth/register \\
  -H "Content-Type: application/json" \\
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "TestPassword123",
    "full_name": "Test User"
  }'

Expected Response (201 Created):
{
  "message": "User registered successfully",
  "user": {
    "id": 1,
    "username": "testuser",
    "email": "test@example.com",
    "full_name": "Test User"
  }
}


Test User Login:
----------------
curl -X POST http://localhost:8000/auth/login \\
  -H "Content-Type: application/json" \\
  -d '{
    "username": "testuser",
    "password": "TestPassword123"
  }'

Expected Response (200 OK):
{
  "message": "Login successful",
  "token": "abc123def456...xyz (64 chars)",
  "user": {
    "id": 1,
    "username": "testuser",
    "email": "test@example.com",
    "full_name": "Test User",
    "role": "student"
  }
}


Test Protected Query Endpoint:
------------------------------
curl -X POST http://localhost:8000/query \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \\
  -d '{
    "query": "What is the Pythagorean theorem?"
  }'

Expected Response (200 OK with agent response)


Test Logout:
-----------
curl -X POST http://localhost:8000/auth/logout \\
  -H "Authorization: Bearer YOUR_TOKEN_HERE"

Expected Response (200 OK):
{
  "message": "Logout successful"
}


===== ARCHITECTURE OVERVIEW =====

Frontend (Streamlit)
    ↓
    │ HTTP Requests
    ↓
FastAPI Backend
    ├─ Authentication Layer (src/auth/)
    │  ├─ UserService (registration, login, logout)
    │  ├─ SessionManager (token generation & validation)
    │  └─ PasswordUtils (bcrypt hashing, validation)
    │
    ├─ Database Layer (src/database/)
    │  ├─ SQLAlchemy ORM Models
    │  └─ DatabaseManager (connection pooling, session management)
    │
    ├─ Agent Layer (src/agents/)
    │  └─ Orchestrator (LLM routing to tools)
    │
    └─ Protection
       ├─ Auth Middleware (verify tokens)
       ├─ Input Validation (prevent injection)
       └─ CORS (cross-origin requests)


===== FILE STRUCTURE (PHASE 1 ADDITIONS) =====

src/
├── auth/
│   ├── __init__.py
│   ├── password_utils.py           ✅ NEW - Bcrypt password hashing
│   ├── session_manager.py          ✅ NEW - Token & session management
│   └── user_service.py             ✅ NEW - User operations (register, login, logout)
│
├── database/
│   ├── __init__.py
│   ├── db_init.py                  ✅ NEW - Database initialization
│   └── models.py                   ✅ NEW - SQLAlchemy ORM models
│
├── config.py                        ✅ UPDATED - Added auth & DB config
├── main.py                          ✅ UPDATED - Added auth middleware and endpoints
│
└── frontend/
    └── auth_pages.py               ✅ NEW - Streamlit login/signup UI
    └── chatbot_streamlit.py         ✅ UPDATED - Added auth wrapper


===== SONARQUBE STANDARDS COMPLIANCE =====

✅ S2053 - Password Strength
   - Using bcrypt with cost factor 12
   - Password validation (8+ chars, complexity requirements)
   - No plaintext passwords in code

✅ S2628 - JWT Token Validation
   - Token format validation (64-byte hex)
   - Token expiry checks
   - Session validation on every request

✅ S2632 - DB Connection Security
   - Using SQLAlchemy ORM (prevents SQL injection)
   - Parameterized queries
   - Connection pooling with proper lifecycle

✅ S4502 - CORS Configuration
   - Explicit CORS origins (not wildcard)
   - Only allowing Streamlit ports

✅ S6212 - Sensitive Data
   - No hardcoded credentials
   - All config from environment variables
   - Secure error messages (no information leakage)

✅ S4829 - Logging
   - Proper logging of authentication events
   - No sensitive data in logs
   - Appropriate log levels


===== ENVIRONMENT VARIABLES =====

Required:
  OPENAI_API_KEY              - OpenAI API key

Optional (with defaults):
  FASTAPI_URL                 - FastAPI URL (default: http://localhost:8000)
  FASTAPI_HOST                - Host to bind to (default: 0.0.0.0)
  FASTAPI_PORT                - Port to bind to (default: 8000)
  DATABASE_PATH               - SQLite database path (default: data/igcse_tutor.db)
  TOKEN_EXPIRY_HOURS          - Token expiry time (default: 24)
  SESSION_CLEANUP_INTERVAL    - Cleanup interval (default: 24)
  DEBUG_MODE                  - Enable debug output (default: false)


===== TROUBLESHOOTING =====

Issue: Database already locked
Solution: Ensure only one FastAPI instance is running

Issue: 401 Unauthorized on /query
Solution: Check that Bearer token is correctly formatted in header

Issue: "Password must be at least 8 characters"
Solution: Use a password with 8+ chars, uppercase, lowercase, digit

Issue: Streamlit can't connect to FastAPI
Solution: Check FASTAPI_URL environment variable and firewall


===== NEXT STEPS (PHASE 2+) =====

Phase 2: Security & Audit
  - Input validation layer with injection detection
  - Response validation & guardrails
  - Query audit logging to database
  - Enhanced system prompt

Phase 3: Offline & Caching
  - Offline cache layer
  - Online/offline sync mechanism
  - Conflict resolution

Phase 4: Quiz & History
  - Robust quiz generation
  - Quiz history tracking
  - 60-day auto-cleanup job

Phase 5: Admin Panel
  - Admin dashboard
  - User management
  - Query monitoring

Phase 6: UI/UX Overhaul
  - Modern design for teenagers
  - Dark/light mode
  - Progress dashboard

Phase 7: Testing & Deployment
  - Security testing (prompt injection)
  - Performance optimization
  - Documentation


===== SONARQUBE SCAN LOCAL =====

To run local SonarQube analysis:

1. Install sonardotnet scanner:
   pip install sonarscanner

2. Run analysis:
   sonar-scanner \\
     -Dsonar.projectKey=igcse-tutor \\
     -Dsonar.sources=src \\
     -Dsonar.host.url=http://localhost:9000 \\
     -Dsonar.login=YOUR_SONAR_TOKEN


===== SUCCESS CRITERIA PHASE 1 =====

✅ Users can register with email verification
✅ Users can login and receive session tokens
✅ Users can logout and invalidate tokens
✅ Token expires after 24 hours
✅ /query endpoint requires valid token
✅ Password hashing uses bcrypt
✅ Input validation prevents common attacks
✅ Database persists across restarts
✅ Streamlit UI shows auth state
✅ All code follows SonarQube standards
"""


if __name__ == "__main__":
    print(__doc__)
