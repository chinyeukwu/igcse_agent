# Phase 6 Quick Reference Guide

## 🚀 Quick Start (5 minutes)

### 1. Install
```bash
pip install -r phase6_requirements.txt
```

### 2. Configure
```bash
cd c:\projects\agenticaitutor
cp .env.example .env  # or create .env
# Edit .env with your settings
```

### 3. Setup
```bash
python setup_phase6.py
```

### 4. Run
```bash
# Terminal 1: Backend
python src/main.py

# Terminal 2: Admin Dashboard  
streamlit run src/frontend/admin_dashboard.py

# Terminal 3: Analytics Dashboard
streamlit run src/frontend/analytics_dashboard.py --logger.level=error
```

### 5. Access
- Admin Dashboard: http://localhost:8501
- Analytics Dashboard: http://localhost:8501
- API Docs: http://localhost:8000/docs

---

## 📁 All Files Created

### Python Modules (5 files)

1. **src/frontend/admin_dashboard.py** (580 lines)
   - Admin dashboard interface
   - User management, security monitoring
   - System statistics, configuration

2. **src/analytics/advanced_analytics.py** (650 lines)
   - Trend detection, anomaly detection
   - Statistical analysis
   - Learning patterns, insights, predictions

3. **src/frontend/analytics_dashboard.py** (520 lines)
   - Analytics UI with 5 views
   - Interactive visualizations
   - Real-time data display

4. **src/api/admin_analytics_routes.py** (650 lines)
   - 24 API endpoints
   - Admin and analytics routes
   - Error handling, validation

5. **src/tools/security_utils.py** (420 lines)
   - JWT authentication
   - Rate limiting, audit logging
   - Session management, MFA

### Documentation (8 files)

1. **PHASE6_GUIDE.md** (1000+ lines)
   - Complete implementation guide
   - Component descriptions, API reference
   - Configuration, integration

2. **PHASE6_SUMMARY.md** (1200+ lines)
   - Feature overview
   - Installation steps
   - Achievements, metrics

3. **PHASE6_CHECKLIST.md** (1100+ lines)
   - Pre-implementation checklist
   - Installation tasks
   - Testing, deployment checklist

4. **PHASE6_TROUBLESHOOTING.md** (1200+ lines)
   - 50+ common issues
   - Solutions and prevention
   - Testing procedures

5. **PHASE6_DEPLOYMENT_PLAYBOOK.md** (1000+ lines)
   - Pre-deployment planning
   - Database migration
   - Service deployment, verification

6. **PHASE6_INDEX.md** (800+ lines)
   - Complete deliverables index
   - Feature matrix
   - Success metrics

7. **PHASE6_COMPLETION_SUMMARY.md** (800+ lines)
   - Final status report
   - Metrics and validation
   - Deployment readiness

8. **PHASE6_QUICK_REFERENCE.md** (this file)
   - Quick start guide
   - Command reference
   - File index

### Configuration (3 files)

1. **phase6_requirements.txt** (40+ packages)
   - All dependencies
   - Numpy, SciPy, Plotly, FastAPI, Streamlit, etc.

2. **setup_phase6.py** (400 lines)
   - Automated setup script
   - Dependency verification
   - Configuration guide

3. **.env.example** (template)
   - Environment variables template
   - Secrets management

---

## 🎯 Common Tasks

### Start Development
```bash
# 1. Install
pip install -r phase6_requirements.txt

# 2. Setup
python setup_phase6.py

# 3. Run backend
python src/main.py

# 4. Run dashboard (new terminal)
streamlit run src/frontend/admin_dashboard.py

# 5. Access at http://localhost:8501
```

### Deploy to Production
```bash
# 1. Backup database
./scripts/backup_database.sh

# 2. Deploy code
bash deploy.sh

# 3. Verify
bash verify.sh

# 4. Check logs
tail -f /var/log/agentic-ai-tutor/app.log
```

### Troubleshoot
```bash
# Check services
systemctl status agentic-api

# Check logs
grep ERROR /var/log/agentic-ai-tutor/app.log

# Test API
curl http://localhost:8000/docs

# Verify database
psql -U admin -d agentic_ai_tutor -c "SELECT 1;"
```

### Run Tests
```bash
# All tests
pytest src/

# Specific test
pytest src/analytics/test_analytics.py

# With coverage
pytest --cov=src/
```

---

## 📊 API Endpoints Reference

### Admin Routes
```
GET    /admin/dashboard/stats
GET    /admin/users?skip=0&limit=10
GET    /admin/user/{user_id}
POST   /admin/user/{user_id}/action
GET    /admin/security-alerts
GET    /admin/dashboard/usage
POST   /admin/cleanup
```

### Analytics Routes
```
GET    /analytics/user?days=30
GET    /analytics/performance
GET    /analytics/learning-patterns
GET    /analytics/user/quiz-scores
GET    /analytics/insights
POST   /analytics/export-report
GET    /analytics/trends?metric=quiz_scores&window_size=7
GET    /analytics/anomalies?metric=quiz_scores
```

---

## 🔐 Security Essentials

### Generate Admin Token
```python
from src.tools.security_utils import TokenManager

token = TokenManager.create_admin_token(
    user_id=1,
    username="admin"
)
print(token)
```

### Use in API Calls
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:8000/admin/dashboard/stats
```

### Rate Limiting Config
```python
# src/tools/security_utils.py
MAX_LOGIN_ATTEMPTS = 5          # Failed attempts
LOCKOUT_DURATION_MINUTES = 15   # Lockout time
```

---

## 📈 Analytics Usage

### Create Engine
```python
from src.analytics.advanced_analytics import AnalyticsEngine

engine = AnalyticsEngine()
```

### Detect Trends
```python
data = [(datetime.now() - timedelta(days=i), 70+i) 
        for i in range(10)]
trend = engine.detect_trend(data)
print(f"Trend: {trend.direction}")
```

### Generate Insights
```python
insights = engine.generate_insights(
    quiz_data={"scores": [75, 80, 85, 90]},
    user_profile={"id": 1},
    activity_log=[...]
)
```

### Detect Anomalies
```python
anomalies = engine.detect_anomalies(
    data=[70, 72, 71, 73, 150],  # 150 is outlier
    method="zscore"
)
```

---

## 📋 Database Quick Reference

### Create Tables
```sql
-- Run these SQL commands
CREATE TABLE audit_logs (...);
CREATE TABLE security_alerts (...);
CREATE TABLE admin_sessions (...);
CREATE TABLE activity_logs (...);
CREATE TABLE cache_entries (...);

-- Create indexes
CREATE INDEX idx_audit_logs_admin_id ON audit_logs(admin_id);
-- ... more indexes
```

### Query Examples
```sql
-- Get admin actions
SELECT * FROM audit_logs WHERE admin_id = 1 ORDER BY timestamp DESC;

-- Get security alerts
SELECT * FROM security_alerts WHERE severity = 'high';

-- Count audit entries
SELECT COUNT(*) FROM audit_logs;
```

---

## 🛠️ Troubleshooting Cheat Sheet

### Issue: API Won't Start
```bash
# Check port availability
netstat -an | grep :8000

# Check Python version
python --version  # Need 3.10+

# Check imports
python -c "import fastapi; print('OK')"

# See full error
python src/main.py
```

### Issue: Dashboard Won't Load
```bash
# Check backend running
curl http://localhost:8000/docs

# Check token
echo $ADMIN_TOKEN  # Should not be empty

# Check Streamlit
streamlit --version

# See error in console output
```

### Issue: Database Connection
```bash
# Test connection
psql -U admin -d agentic_ai_tutor -c "SELECT 1;"

# Check URL format
# Connection: postgresql://user:password@host:port/dbname

# Check if DB exists
createdb agentic_ai_tutor
```

---

## 📞 Get Help

### Documentation
- **PHASE6_GUIDE.md** - Implementation details
- **PHASE6_TROUBLESHOOTING.md** - Common issues
- **PHASE6_DEPLOYMENT_PLAYBOOK.md** - Production setup

### Code Examples
```python
# In any module:
from src.analytics.advanced_analytics import AnalyticsEngine
from src.frontend.admin_dashboard import render_admin_dashboard
from src.tools.security_utils import TokenManager
```

### Run Setup
```bash
python setup_phase6.py  # Interactive setup guide
```

---

## ✅ Deployment Checklist

- [ ] Install dependencies
- [ ] Configure .env file
- [ ] Create database tables
- [ ] Create admin user
- [ ] Test API endpoints
- [ ] Test dashboards
- [ ] Run verification script
- [ ] Check monitoring
- [ ] Document URLs
- [ ] Train team

---

## 🎯 Performance Tips

### For Admin Dashboard
- Use pagination for user lists
- Limit displayed data
- Enable caching

### For Analytics
- Use time windows (last 7 days)
- Batch calculations
- Cache results

### For API
- Enable connection pooling
- Use database indexes
- Implement caching

---

## 📱 URLs Reference

| Service | URL | Port |
|---------|-----|------|
| API Docs | http://localhost:8000/docs | 8000 |
| Admin Dashboard | http://localhost:8501 | 8501 |
| Analytics Dashboard | http://localhost:8501 | 8501 |
| Database | localhost:5432 | 5432 |
| Redis Cache | localhost:6379 | 6379 |

---

## 🔑 Credentials Template

```
ADMIN_USER: admin
ADMIN_EMAIL: admin@example.com
ADMIN_TOKEN: [generated via TokenManager]

DB_HOST: localhost
DB_USER: admin
DB_PASSWORD: secure_password
DB_NAME: agentic_ai_tutor

SECRET_KEY: [generated via secrets.token_urlsafe(32)]
ALGORITHM: HS256
```

---

## 📚 File Locations

```
Project Root:
  src/
    frontend/
      ├── admin_dashboard.py ← Admin UI
      └── analytics_dashboard.py ← Analytics UI
    analytics/
      └── advanced_analytics.py ← Analytics Engine
    api/
      └── admin_analytics_routes.py ← API Routes
    tools/
      └── security_utils.py ← Security Layer
  Documentation/
    ├── PHASE6_GUIDE.md
    ├── PHASE6_SUMMARY.md
    ├── PHASE6_CHECKLIST.md
    ├── PHASE6_TROUBLESHOOTING.md
    ├── PHASE6_DEPLOYMENT_PLAYBOOK.md
    └── PHASE6_INDEX.md
  phase6_requirements.txt
  setup_phase6.py
```

---

## 🚀 Next Steps

1. **Immediate (Today)**
   - [ ] Read this quick reference
   - [ ] Install phase6_requirements.txt
   - [ ] Run setup_phase6.py

2. **This Week**
   - [ ] Read PHASE6_GUIDE.md
   - [ ] Deploy to staging
   - [ ] Run tests

3. **Next Week**
   - [ ] Train team
   - [ ] Deploy to production
   - [ ] Monitor

---

## 💾 Save These

Print or bookmark:
- **PHASE6_GUIDE.md** - Your Bible
- **PHASE6_TROUBLESHOOTING.md** - Your Lifesaver
- This quick reference - For daily use

---

**Version:** 1.0  
**Last Updated:** January 2024  
**Status:** ✅ Production Ready

For detailed information, see PHASE6_GUIDE.md
