# Phase 1: Quick Reference Guide

## 🚀 Fast Start

### Prerequisites
```powershell
# Activate virtual environment
& c:\projects\agenticaitutor\mytutor\Scripts\Activate.ps1
```

### Start Development Servers

**Terminal 1 - FastAPI Backend:**
```powershell
cd c:\projects\agenticaitutor
& c:\projects\agenticaitutor\mytutor\Scripts\Activate.ps1
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2 - Streamlit Frontend:**
```powershell
cd c:\projects\agenticaitutor
& c:\projects\agenticaitutor\mytutor\Scripts\Activate.ps1
streamlit run src/frontend/chatbot_streamlit.py
```

### Access Points
- **UI**: http://localhost:8501
- **API Docs**: http://localhost:8000/docs
- **Database**: `data/igcse_tutor.db`

---

## 🔒 Authentication Flow

### 1. Register User
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "student1",
    "email": "student@example.com",
    "password": "SecurePass123",
    "full_name": "John Student"
  }'
```

### 2. Login
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "student1",
    "password": "SecurePass123"
  }'
```

**Response includes token:**
```json
{
  "token": "abc123...xyz (64 chars)",
  "user": {
    "id": 1,
    "username": "student1",
    "role": "student"
  }
}
```

### 3. Use Token for Protected Endpoints
```bash
curl -X POST http://localhost:8000/query \
  -H "Authorization: Bearer abc123...xyz" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is Newton'\''s first law?"}'
```

### 4. Logout
```bash
curl -X POST http://localhost:8000/auth/logout \
  -H "Authorization: Bearer abc123...xyz"
```

---

## 📁 Key Files

### Models & Database
- `src/database/models.py` - SQLAlchemy ORM definitions
- `src/database/db_init.py` - Database manager & initialization
- `src/auth/user_service.py` - User operations (CRUD)

### Security
- `src/auth/password_utils.py` - Bcrypt hashing/verification
- `src/auth/session_manager.py` - Token generation/validation

### API
- `src/main.py` - FastAPI app with auth endpoints
- `src/config.py` - Configuration management

### UI
- `src/frontend/auth_pages.py` - Login/signup Streamlit pages
- `src/frontend/chatbot_streamlit.py` - Main Streamlit app

### Testing
- `test_phase1.py` - Automated test suite

---

## 🔧 Common Tasks

### Add New User Manually (Python)
```python
from src.database import get_db_manager
from src.auth import UserService

db_manager = get_db_manager()
with db_manager.get_session() as session:
    success, error, user = UserService.register_user(
        session,
        username="newuser",
        email="new@example.com",
        password="Password123",
    )
    if success:
        print(f"User created: {user.username}")
```

### Check User Login Status
```python
from src.database import get_db_manager
from src.auth import UserService

# Using token
token = "your_64_char_token"
db_manager = get_db_manager()
with db_manager.get_session() as session:
    is_valid, user = UserService.verify_session(session, token)
    if is_valid:
        print(f"Token valid for user: {user.username}")
```

### Debug SQL Queries
Edit `src/config.py`:
```python
sql_echo = os.getenv("SQL_ECHO", "true").lower() == "true"
```

Then check terminal output to see all SQL queries.

---

## 🐛 Troubleshooting

### "ModuleNotFoundError: No module named 'bcrypt'"
```powershell
& c:\projects\agenticaitutor\mytutor\Scripts\Activate.ps1
pip install bcrypt email-validator
```

### "Database is locked"
- Ensure only one FastAPI instance is running
- Close any active database connections

### "401 Unauthorized" on /query
- Check Authorization header format: `Bearer TOKEN_HERE`
- Verify token is valid (not expired)
- Token format should be 64 hexadecimal characters

### "Password must be at least 8 characters"
- Password must be 8+ characters
- Must include uppercase + lowercase + digit
- Example: `SecurePass123`

### Streamlit can't connect to API
- Verify FastAPI is running (`uvicorn` terminal active)
- Check FASTAPI_URL matches API port (default 8000)
- Check firewall/network connectivity

---

## 🧪 Run Tests

```powershell
& c:\projects\agenticaitutor\mytutor\Scripts\Activate.ps1
python test_phase1.py
```

**Expected Output:**
```
✅ PASS - Database Initialization
✅ PASS - User Registration
✅ PASS - User Login
✅ PASS - Session Verification
✅ PASS - User Logout
✅ PASS - Password Utilities
Result: 6/6 tests passed
```

---

## 📊 Database Schema

### users
```sql
id             INTEGER PRIMARY KEY
username       VARCHAR(50) UNIQUE
email          VARCHAR(120) UNIQUE
password_hash  VARCHAR(255)
full_name      VARCHAR(120)
role           VARCHAR(20) DEFAULT 'student'
created_at     DATETIME DEFAULT NOW()
last_login     DATETIME
is_active      BOOLEAN DEFAULT TRUE
```

### sessions
```sql
id         INTEGER PRIMARY KEY
user_id    INTEGER FOREIGN KEY
token      VARCHAR(500) UNIQUE
expires_at DATETIME
created_at DATETIME DEFAULT NOW()
ip_address VARCHAR(45)
```

### quiz_history
```sql
id               INTEGER PRIMARY KEY
user_id          INTEGER FOREIGN KEY
subject          VARCHAR(50)
topic            VARCHAR(150)
difficulty       VARCHAR(20)
language_code    VARCHAR(5) DEFAULT 'en'
questions_json   TEXT
user_answers_json TEXT
score            FLOAT
time_taken_seconds INTEGER
created_at       DATETIME DEFAULT NOW()
is_offline       BOOLEAN DEFAULT FALSE
synced_at        DATETIME
```

---

## 🔐 Security Checklist

✅ Passwords hashed with bcrypt (cost 12)
✅ Tokens are 64-byte random hex
✅ Tokens expire after 24 hours
✅ Sessions validated on each request
✅ SQL injection prevented (ORM)
✅ No hardcoded credentials
✅ CORS restricted (not wildcard)
✅ Error messages safe (no info leakage)
✅ Input validation on all endpoints
✅ Password strength enforced

---

## 📋 API Response Examples

### Registration Success (201)
```json
{
  "message": "User registered successfully",
  "user": {
    "id": 1,
    "username": "student1",
    "email": "student@example.com",
    "full_name": "John Student"
  }
}
```

### Login Success (200)
```json
{
  "message": "Login successful",
  "token": "e868d3c462ba47b4f0a45c9afb44a2ac86d3c94de81b7d2e5c3f9a2b1e068f9",
  "user": {
    "id": 1,
    "username": "student1",
    "email": "student@example.com",
    "role": "student"
  }
}
```

### Query Success (200)
```json
{
  "data": "Newton's first law states that an object at rest stays at rest...",
  "type": "text"
}
```

### Error Response (400)
```json
{
  "detail": "Username must be 3-50 characters"
}
```

### Unauthorized (401)
```json
{
  "detail": "Invalid or expired token"
}
```

---

## 🎯 Environment Variables

```bash
# API Server
FASTAPI_URL=http://localhost:8000
FASTAPI_HOST=0.0.0.0
FASTAPI_PORT=8000

# Authentication
TOKEN_EXPIRY_HOURS=24
MAX_LOGIN_ATTEMPTS=5
MIN_PASSWORD_LENGTH=8

# Database
DATABASE_PATH=data/igcse_tutor.db

# Data Retention
QUIZ_HISTORY_RETENTION_DAYS=60
AUDIT_LOG_RETENTION_DAYS=90

# Features
ENABLE_OFFLINE_MODE=true
ENABLE_QUIZ_GENERATION=true
ENABLE_ADMIN_PANEL=true

# Development
DEBUG_MODE=false
LOG_LEVEL=INFO
```

---

## 📞 Support

**For issues:**
1. Check troubleshooting section above
2. Verify virtual environment is activated
3. Check terminal for error messages
4. Run `test_phase1.py` to diagnose issues
5. Review PHASE1_SETUP_GUIDE.md for detailed info

**For improvements:**
- Phase 2 implementations documented in todo list
- Follow SonarQube standards in new code
- Update tests when adding features
- Document configuration in config.py

---

**Last Updated**: February 22, 2026
**Phase Status**: ✅ COMPLETE & TESTED
