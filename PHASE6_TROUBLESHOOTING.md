# Phase 6 Troubleshooting Guide

## Installation Issues

### Issue: Dependencies Installation Fails

**Symptoms:**
- `pip install` command fails with error
- Missing package errors
- Version conflict messages

**Solutions:**

1. **Update pip first:**
```bash
python -m pip install --upgrade pip
```

2. **Install with specific Python version:**
```bash
python3.11 -m pip install -r phase6_requirements.txt
```

3. **Check for conflicting packages:**
```bash
pip check
```

4. **Install compatible versions:**
```bash
pip install -r phase6_requirements.txt --upgrade
```

5. **Use conda instead:**
```bash
conda create -n phase6 python=3.11
conda activate phase6
pip install -r phase6_requirements.txt
```

**Prevention:**
- Always use virtual environments
- Upgrade pip before installing
- Test in staging environment first

---

### Issue: NumPy/SciPy Installation Error on Windows

**Symptoms:**
- `error: Microsoft Visual C++ 14.0 is required`
- `Building wheel for scipy failed`

**Solutions:**

1. **Install Microsoft C++ Build Tools:**
   - Download from: https://visualstudio.microsoft.com/visual-cpp-build-tools/
   - Install with Windows SDK

2. **Use pre-compiled wheels:**
```bash
pip install numpy scipy --only-binary :all:
```

3. **Use conda (easier on Windows):**
```bash
conda install numpy scipy
```

---

## Configuration Issues

### Issue: SECRET_KEY Not Changed

**Symptoms:**
- Using default secret key in production
- Security warnings in logs
- Suspected token compromise

**Solutions:**

1. **Generate secure key:**
```python
import secrets
secret_key = secrets.token_urlsafe(32)
print(secret_key)
```

2. **Update security_utils.py:**
```python
class SecurityConfig:
    SECRET_KEY = "your-generated-secret-key"
```

3. **Never commit secrets:**
```bash
# Add to .gitignore
src/tools/security_utils.py
.env
```

4. **Use environment variables:**
```python
import os
SECRET_KEY = os.getenv("ADMIN_SECRET_KEY", default_value)
```

**Prevention:**
- Use environment variables for secrets
- Never hardcode credentials
- Use git hooks to prevent accidental commits

---

### Issue: Database Connection Fails

**Symptoms:**
- `postgresql connection failed`
- `database does not exist`
- `authentication failed`

**Solutions:**

1. **Verify database is running:**
```bash
# For PostgreSQL
psql -U postgres
```

2. **Check connection string:**
```python
# Correct format:
DATABASE_URL = "postgresql://user:password@localhost:5432/dbname"

# Not:
DATABASE_URL = "postgresql://localhost/dbname"
```

3. **Test connection:**
```python
import asyncio
import databases

async def test_connection():
    database = databases.Database(DATABASE_URL)
    await database.connect()
    print("Connected successfully")
    await database.disconnect()

asyncio.run(test_connection())
```

4. **Create database if missing:**
```bash
createdb agentic_ai_tutor
```

5. **Check permissions:**
```bash
psql -U postgres
GRANT ALL PRIVILEGES ON DATABASE agentic_ai_tutor TO admin;
```

---

## Authentication Issues

### Issue: Admin Login Fails

**Symptoms:**
- "Invalid credentials" error
- "User not found"
- "Admin privileges required"

**Solutions:**

1. **Verify admin user exists:**
```sql
SELECT * FROM users WHERE is_admin = true;
```

2. **Check admin status:**
```sql
UPDATE users SET is_admin = true, is_active = true WHERE username = 'admin';
```

3. **Verify token format:**
```python
from src.tools.security_utils import TokenManager

# Check token validity
try:
    payload = TokenManager.verify_token(token)
    print("Token valid:", payload)
except Exception as e:
    print("Token error:", e)
```

4. **Check token expiration:**
```python
import jwt
from src.tools.security_utils import SecurityConfig

payload = jwt.decode(token, SecurityConfig.SECRET_KEY, algorithms=[SecurityConfig.ALGORITHM])
print("Expires at:", payload.get("exp"))
```

---

### Issue: Rate Limiting Blocks Admin

**Symptoms:**
- "Too many attempts" error
- Admin account locked for 15 minutes
- Cannot login after failed attempts

**Solutions:**

1. **Check rate limiter status:**
```python
from src.tools.security_utils import rate_limiter

# Check if locked
is_locked = rate_limiter.is_rate_limited("admin@email.com")
print("Locked:", is_locked)
```

2. **Reset rate limiter:**
```python
from src.tools.security_utils import rate_limiter

rate_limiter.reset_attempts("admin@email.com")
print("Rate limit reset")
```

3. **Adjust rate limiting settings:**
```python
# src/tools/security_utils.py
class SecurityConfig:
    MAX_LOGIN_ATTEMPTS = 5  # Increase if too strict
    LOCKOUT_DURATION_MINUTES = 15  # Adjust timeout
```

---

### Issue: MFA Code Not Received

**Symptoms:**
- MFA code not generating
- MFA code verification fails

**Solutions:**

1. **Check MFA is enabled:**
```python
from src.tools.security_utils import SecurityConfig

print("MFA Required:", SecurityConfig.REQUIRE_MFA_FOR_ADMIN)
```

2. **Generate test code:**
```python
from src.tools.security_utils import MFAHandler

code = MFAHandler.generate_mfa_code()
print("Generated code:", code)
```

3. **Verify code format:**
```python
# Code should be 6 digits
if len(code) == 6 and code.isdigit():
    print("Code format valid")
```

4. **Check email/SMS service:**
- Verify service is running
- Check API keys
- Review logs for failures

---

## API Issues

### Issue: API Endpoints Return 401 Unauthorized

**Symptoms:**
- All API requests fail with 401
- "Invalid token" error

**Solutions:**

1. **Check Authorization header:**
```python
# Correct:
headers = {"Authorization": "Bearer your-token-here"}

# Incorrect:
headers = {"Authorization": "your-token-here"}  # Missing "Bearer"
headers = {"Authorization": f"JWT {token}"}  # Wrong scheme
```

2. **Verify token is valid:**
```bash
curl -H "Authorization: Bearer token" http://localhost:8000/admin/dashboard/stats
```

3. **Check token expiration:**
```python
import time
payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
if payload["exp"] < time.time():
    print("Token expired")
```

4. **Generate new token:**
```python
from src.tools.security_utils import TokenManager

new_token = TokenManager.create_admin_token(user_id=1, username="admin")
print("New token:", new_token)
```

---

### Issue: API Returns 403 Forbidden

**Symptoms:**
- "Admin privileges required" error
- User is authenticated but not authorized

**Solutions:**

1. **Verify user is admin:**
```sql
SELECT id, username, is_admin FROM users WHERE id = 1;
```

2. **Update user to admin:**
```sql
UPDATE users SET is_admin = true WHERE id = 1;
```

3. **Check token scope:**
```python
payload = TokenManager.verify_token(token)
print("Scope:", payload.get("scope"))  # Should be "admin"
```

4. **Recreate admin token:**
```python
token = TokenManager.create_admin_token(user_id=1, username="admin")
```

---

### Issue: API Returns 500 Internal Server Error

**Symptoms:**
- Generic error response
- No specific error message

**Solutions:**

1. **Check application logs:**
```bash
tail -f logs/api_errors.log
```

2. **Enable debug mode:**
```python
# src/main.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

3. **Test endpoint directly:**
```python
import requests
response = requests.get("http://localhost:8000/admin/dashboard/stats")
print("Status:", response.status_code)
print("Response:", response.json())
```

4. **Check database connection:**
```python
# Try a simple database query
async def test_db():
    result = await db.fetch("SELECT 1")
    print("DB connection OK")
```

---

## Database Issues

### Issue: Tables Not Found

**Symptoms:**
- `relation "audit_logs" does not exist`
- `table not found` errors

**Solutions:**

1. **List existing tables:**
```sql
\dt
SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';
```

2. **Create missing tables:**
```sql
-- Run table creation scripts from PHASE6_CHECKLIST.md
CREATE TABLE audit_logs (...)
CREATE TABLE security_alerts (...)
-- etc.
```

3. **Run migrations:**
```bash
# If using Alembic
alembic upgrade head
```

---

### Issue: Foreign Key Constraint Violations

**Symptoms:**
- `foreign key constraint failed`
- Cannot insert/update rows

**Solutions:**

1. **Check referenced records exist:**
```sql
-- For admin_id in audit_logs
SELECT * FROM users WHERE id = 1;
```

2. **Disable FK temporarily (development only):**
```sql
SET session_replication_role = replica;
-- Make changes
SET session_replication_role = default;
```

3. **Add missing parent records:**
```sql
INSERT INTO users (id, username, email, is_admin) 
VALUES (1, 'admin', 'admin@example.com', true);
```

---

### Issue: Slow Query Performance

**Symptoms:**
- Queries taking >1 second
- Dashboard loading slowly

**Solutions:**

1. **Check indexes:**
```sql
SELECT * FROM pg_indexes WHERE tablename = 'audit_logs';
```

2. **Create missing indexes:**
```sql
CREATE INDEX idx_audit_logs_timestamp ON audit_logs(timestamp DESC);
CREATE INDEX idx_audit_logs_admin_id ON audit_logs(admin_id);
```

3. **Analyze query plan:**
```sql
EXPLAIN ANALYZE SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT 10;
```

4. **Optimize index strategy:**
```sql
-- Use compound indexes for common queries
CREATE INDEX idx_audit_logs_admin_ts ON audit_logs(admin_id, timestamp DESC);
```

---

## Streamlit Issues

### Issue: Streamlit Dashboard Won't Load

**Symptoms:**
- Dashboard page is blank
- "Connection refused" error

**Solutions:**

1. **Start backend API first:**
```bash
# Terminal 1
python src/main.py

# Terminal 2  
streamlit run src/frontend/admin_dashboard.py
```

2. **Check API is running:**
```bash
curl http://localhost:8000/admin/dashboard/stats
```

3. **Verify token is set:**
```python
import streamlit as st
token = st.session_state.get("auth_token")
print("Token available:", bool(token))
```

4. **Check firewall/ports:**
- FastAPI: port 8000
- Streamlit: port 8501

---

### Issue: Streamlit Charts Not Rendering

**Symptoms:**
- Charts show as blank
- Plotly charts don't load

**Solutions:**

1. **Verify Plotly installation:**
```bash
pip install plotly --upgrade
```

2. **Check data format:**
```python
import plotly.express as px
import pandas as pd

# Data must be properly formatted
df = pd.DataFrame({
    'x': [1, 2, 3],
    'y': [4, 5, 6]
})
fig = px.scatter(df, x='x', y='y')
```

3. **Use st.plotly_chart():**
```python
import streamlit as st
st.plotly_chart(fig, use_container_width=True)
```

---

### Issue: Streamlit Caching Issues

**Symptoms:**
- Old data displayed
- Cache not updating

**Solutions:**

1. **Clear cache:**
```bash
# Manually
streamlit cache clear

# Or in code
streamlit.cache_data.clear()
```

2. **Add cache parameters:**
```python
@st.cache_data(ttl=300)  # 5 minute TTL
def get_data():
    # Function body
```

3. **Disable cache temporarily:**
```python
@st.cache_data(max_entries=0)  # Disables caching
def get_data():
    # Function body
```

---

## Analytics Issues

### Issue: Analytics Engine Returns No Data

**Symptoms:**
- Analytics functions return empty
- No insights generated

**Solutions:**

1. **Check data availability:**
```python
from src.analytics.advanced_analytics import AnalyticsEngine

engine = AnalyticsEngine()
data = [70, 72, 75, 78, 80]
stats = engine.calculate_statistics(data)
print("Stats:", stats)
```

2. **Verify data format:**
```python
# Data must be list of floats/ints
data = [float(x) for x in quiz_scores]

# For trends, need datetime tuples
data_points = [(datetime.now(), score), ...]
```

3. **Check minimum data points:**
```python
# Most functions need minimum 2-3 data points
if len(data) < 3:
    print("Insufficient data")
```

---

### Issue: Trend Detection Not Working

**Symptoms:**
- Trend direction is "stable" for clear trends
- Trend strength is 0

**Solutions:**

1. **Use sufficient data points:**
```python
# Need at least 7-10 points for reliable trends
trend = engine.detect_trend(data_points, window_size=7)
```

2. **Check data variability:**
```python
# Data must have variation to detect trends
data = [70, 70, 70, 70]  # No trend possible
data = [70, 71, 72, 73]  # Clear uptrend
```

3. **Adjust window size:**
```python
# Smaller window for recent trends
trend = engine.detect_trend(data_points, window_size=3)

# Larger window for overall trends
trend = engine.detect_trend(data_points, window_size=14)
```

---

## Performance Issues

### Issue: Dashboard Loading Slowly

**Symptoms:**
- Streamlit app takes >5 seconds to load
- Charts render with lag

**Solutions:**

1. **Enable caching:**
```python
import streamlit as st

@st.cache_data(ttl=300)
def expensive_calculation():
    # Function body
    return result
```

2. **Optimize queries:**
```python
# Bad: Fetches all data
all_data = db.get_all_users()

# Good: Fetch only needed columns and rows
users = db.get_users(limit=10, columns=['id', 'username'])
```

3. **Use pagination:**
```python
response = requests.get(
    "http://localhost:8000/admin/users",
    params={"skip": 0, "limit": 10}
)
```

4. **Reduce chart complexity:**
```python
# Limit number of data points in charts
if len(data) > 1000:
    data = data[::int(len(data)/1000)]  # Sample every Nth point
```

---

### Issue: High Memory Usage

**Symptoms:**
- Application crashes with out of memory
- Performance degrades over time

**Solutions:**

1. **Monitor memory:**
```python
import psutil

memory = psutil.Process().memory_info()
print(f"Memory usage: {memory.rss / 1024 / 1024} MB")
```

2. **Limit cached data:**
```python
# Reduce cache time-to-live
@st.cache_data(ttl=60)  # 1 minute instead of 5
def get_data():
    pass
```

3. **Clear old cache entries:**
```python
# Manually clear in database
DELETE FROM cache_entries WHERE expires_at < NOW();
```

4. **Use streaming for large datasets:**
```python
# Process data in chunks instead of loading all
for chunk in get_data_chunks():
    process(chunk)
```

---

## Security Issues

### Issue: Audit Logs Growing Too Large

**Symptoms:**
- Slow queries on audit tables
- Disk space running out

**Solutions:**

1. **Archive old logs:**
```bash
# Create backup
pg_dump -t audit_logs > audit_logs_backup_2024.sql

# Delete old entries
DELETE FROM audit_logs WHERE timestamp < NOW() - INTERVAL '90 days';
```

2. **Implement log rotation:**
```python
# In periodic maintenance task
from datetime import datetime, timedelta

cutoff = datetime.now() - timedelta(days=90)
db.delete_audit_logs_before(cutoff)
```

3. **Compress old logs:**
```bash
SELECT * INTO audit_logs_archive 
FROM audit_logs 
WHERE timestamp < NOW() - INTERVAL '180 days';

DELETE FROM audit_logs 
WHERE timestamp < NOW() - INTERVAL '180 days';
```

---

### Issue: Security Alert Spam

**Symptoms:**
- Too many false positive alerts
- Alert fatigue

**Solutions:**

1. **Adjust alert thresholds:**
```python
# In security_utils.py
MAX_LOGIN_ATTEMPTS = 5  # Increase if too strict
LOCKOUT_DURATION_MINUTES = 15  # Increase timeout
```

2. **Filter non-critical alerts:**
```python
# Only show critical and high severity
alerts = [a for a in all_alerts if a['severity'] in ['critical', 'high']]
```

3. **Implement alert deduplication:**
```python
# Group similar alerts
from itertools import groupby
unique_alerts = {}
for alert in alerts:
    key = (alert['event_type'], alert['user_id'])
    if key not in unique_alerts or alert['timestamp'] > unique_alerts[key]['timestamp']:
        unique_alerts[key] = alert
```

---

## Getting Help

### Debug Logging
```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
logger.debug("Debug message")
logger.info("Info message")
logger.error("Error message")
```

### Common Log Locations
- FastAPI logs: `logs/api.log`
- Streamlit output: `logs/streamlit.log`
- Database logs: PostgreSQL `postgresql.log`
- Application logs: `logs/app.log`

### Support Resources
- Read PHASE6_GUIDE.md
- Review PHASE6_SUMMARY.md
- Check example implementations
- Run tests with verbose output: `pytest -v`

---

## Testing Procedure

Before asking for help, test:

1. **Dependency check:**
```bash
pip list | grep -E "numpy|scipy|fastapi|streamlit"
```

2. **Database connection:**
```bash
psql -U username -d dbname -c "SELECT 1;"
```

3. **API endpoint:**
```bash
curl -H "Authorization: Bearer token" http://localhost:8000/admin/dashboard/stats
```

4. **Token validity:**
```python
from src.tools.security_utils import TokenManager
TokenManager.verify_token(your_token)
```

5. **Analytics engine:**
```python
from src.analytics.advanced_analytics import AnalyticsEngine
engine = AnalyticsEngine()
result = engine.calculate_statistics([1, 2, 3, 4, 5])
print(result)
```

---

## Issue Report Template

```
Title: [Brief issue description]

Environment:
- Python Version: [version]
- OS: [Windows/Linux/Mac]
- Database: [PostgreSQL version]

Symptom:
[What you see]

Expected Behavior:
[What should happen]

Steps to Reproduce:
1. [Step 1]
2. [Step 2]
3. [Step 3]

Error Messages:
[Any error messages]

Logs:
[Relevant log excerpts]

Solutions Tried:
[What you've already tried]
```

---

**Last Updated:** 2024  
**Version:** 1.0  
**For more information:** See PHASE6_GUIDE.md
