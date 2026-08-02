# Phase 6 Deployment Playbook

> **Complete guide for deploying Phase 6: Admin Dashboard & Advanced Analytics to production**

---

## Table of Contents

1. [Pre-Deployment](#pre-deployment)
2. [Deployment Planning](#deployment-planning)
3. [Environment Setup](#environment-setup)
4. [Database Migration](#database-migration)
5. [Service Deployment](#service-deployment)
6. [Verification & Testing](#verification--testing)
7. [Post-Deployment](#post-deployment)
8. [Rollback Procedures](#rollback-procedures)
9. [Monitoring & Maintenance](#monitoring--maintenance)

---

## Pre-Deployment

### Prerequisites Checklist

#### Infrastructure
- [ ] Production server(s) provisioned
- [ ] Database server configured
- [ ] Redis cache available (optional)
- [ ] SSL certificates obtained
- [ ] Firewall rules configured
- [ ] Load balancer configured (if needed)

#### Preparation
- [ ] Code review completed
- [ ] Security audit passed
- [ ] Performance testing completed
- [ ] Staging deployment verified
- [ ] Team trained
- [ ] Documentation reviewed

#### Configuration
- [ ] Production secrets prepared (not in repo)
- [ ] Environment variables documented
- [ ] Database backups automated
- [ ] Monitoring configured
- [ ] Logging configured
- [ ] Alerting configured

### Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|-----------|
| Database migration fails | Low | High | Test on staging, have rollback ready |
| API downtime | Low | High | Blue-green deployment |
| Security breach | Very Low | Critical | Follow security checklist |
| Performance degradation | Medium | Medium | Load test, optimize queries |
| Admin lockout | Low | Medium | Have bypass for emergencies |

### Rollback Plan

```
If deployment fails:
1. Stop new services
2. Redirect traffic to previous version
3. Restore database from backup
4. Restart old services
5. Notify stakeholders
6. Investigate root cause
```

---

## Deployment Planning

### Timeline Example (8-hour window)

```
14:00 - Pre-deployment checks begin
14:30 - Final security review
15:00 - Database backup
15:15 - Start code deployment
15:30 - Deploy FastAPI backend
16:00 - Deploy Streamlit dashboards
16:15 - Run smoke tests
16:30 - Enable admin features
16:45 - Final verification
17:00 - Open to users
17:30 - Monitor for issues

Post-deployment:
- 24-hour monitoring
- Team on standby
- Daily health checks for 1 week
```

### Communication Plan

**Before Deployment:**
- Email to all admins: deployment schedule
- Slack notification: 1 day before
- Teams meeting: morning of deployment

**During Deployment:**
- Real-time status updates
- Slack updates every 30 minutes
- Emergency contact ready

**After Deployment:**
- Success notification
- Release notes shared
- Thank you to team

---

## Environment Setup

### 1. Production Environment Variables

Create `.env` file:

```bash
# Database
DATABASE_URL="postgresql://admin:secure_password@prod-db.example.com:5432/agentic_ai_tutor"
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=40

# Redis (Optional)
REDIS_URL="redis://cache.example.com:6379/0"

# Security
ADMIN_SECRET_KEY="generate-with-secrets.token_urlsafe(32)"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=30
ADMIN_SESSION_TIMEOUT_MINUTES=60

# Logging
LOG_LEVEL="INFO"
DEBUG_MODE=False
LOG_FILE="/var/log/agentic-ai-tutor/app.log"

# Application
APP_NAME="Agentic AI Tutor"
APP_VERSION="6.0"
ENVIRONMENT="production"

# Email (for alerts)
EMAIL_HOST="smtp.example.com"
EMAIL_PORT=587
EMAIL_USER="alerts@example.com"
EMAIL_PASSWORD="email_password"

# Monitoring
SENTRY_DSN="https://your-sentry-dsn"
DATADOG_API_KEY="datadog-api-key"
```

**Security Notes:**
- Never commit `.env` to git
- Use secrets management system (Vault, AWS Secrets Manager)
- Rotate secrets quarterly
- Use strong random values (30+ characters for SECRET_KEY)

### 2. Directory Structure

```
/opt/agentic-ai-tutor/
├── app/
│   ├── src/
│   │   ├── frontend/
│   │   ├── analytics/
│   │   ├── api/
│   │   ├── tools/
│   │   ├── models/
│   │   └── main.py
│   ├── logs/
│   │   ├── app.log
│   │   ├── api_errors.log
│   │   ├── admin_activity.log
│   │   └── security.log
│   ├── config/
│   │   └── production.yml
│   ├── data/
│   │   └── premier-league-matches.csv
│   ├── .env
│   ├── requirements.txt
│   ├── phase6_requirements.txt
│   └── README.md
├── venv/
├── backups/
│   └── database/
└── scripts/
    ├── deploy.sh
    ├── verify.sh
    └── rollback.sh
```

### 3. System Service Setup

#### FastAPI Service

Create `/etc/systemd/system/agentic-api.service`:

```ini
[Unit]
Description=Agentic AI Tutor API
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=notify
User=agentic
WorkingDirectory=/opt/agentic-ai-tutor/app
Environment="PATH=/opt/agentic-ai-tutor/venv/bin"
EnvironmentFile=/opt/agentic-ai-tutor/app/.env
ExecStart=/opt/agentic-ai-tutor/venv/bin/uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable agentic-api
sudo systemctl start agentic-api
```

#### Streamlit Services

Create `/etc/systemd/system/agentic-admin.service`:

```ini
[Unit]
Description=Agentic AI Admin Dashboard
After=network.target agentic-api.service
Wants=agentic-api.service

[Service]
Type=simple
User=agentic
WorkingDirectory=/opt/agentic-ai-tutor/app
Environment="PATH=/opt/agentic-ai-tutor/venv/bin"
EnvironmentFile=/opt/agentic-ai-tutor/app/.env
ExecStart=/opt/agentic-ai-tutor/venv/bin/streamlit run src/frontend/admin_dashboard.py --server.port=8501
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

---

## Database Migration

### 1. Pre-Migration Backup

```bash
#!/bin/bash
# backup_database.sh

BACKUP_DIR="/opt/agentic-ai-tutor/backups/database"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DB_NAME="agentic_ai_tutor"

mkdir -p $BACKUP_DIR

# Full database backup
pg_dump \
  --host=$DB_HOST \
  --username=$DB_USER \
  --format=custom \
  --file="$BACKUP_DIR/full_backup_$TIMESTAMP.dump" \
  $DB_NAME

# Backup specific tables
pg_dump \
  --host=$DB_HOST \
  --username=$DB_USER \
  --table=users \
  --table=quiz_attempts \
  --format=custom \
  --file="$BACKUP_DIR/critical_tables_$TIMESTAMP.dump" \
  $DB_NAME

echo "Backup completed: $BACKUP_DIR/full_backup_$TIMESTAMP.dump"
```

### 2. Create Required Tables

```sql
-- Run as database owner
\c agentic_ai_tutor

-- Audit Logs Table
CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    admin_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    action VARCHAR(100) NOT NULL,
    resource VARCHAR(255),
    details JSONB DEFAULT '{}',
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_date DATE DEFAULT CURRENT_DATE
);

-- Security Alerts Table
CREATE TABLE IF NOT EXISTS security_alerts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    event_type VARCHAR(100) NOT NULL,
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    details JSONB DEFAULT '{}',
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved BOOLEAN DEFAULT FALSE
);

-- Admin Sessions Table
CREATE TABLE IF NOT EXISTS admin_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(500),
    ip_address VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    active BOOLEAN DEFAULT TRUE
);

-- Activity Logs Table
CREATE TABLE IF NOT EXISTS activity_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type VARCHAR(50),
    subject_id VARCHAR(100),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    details JSONB DEFAULT '{}'
);

-- Cache Entries Table
CREATE TABLE IF NOT EXISTS cache_entries (
    key VARCHAR(255) PRIMARY KEY,
    value TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_audit_logs_admin_id ON audit_logs(admin_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_security_alerts_user_id ON security_alerts(user_id);
CREATE INDEX IF NOT EXISTS idx_security_alerts_timestamp ON security_alerts(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_security_alerts_severity ON security_alerts(severity);
CREATE INDEX IF NOT EXISTS idx_admin_sessions_user_id ON admin_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_admin_sessions_active ON admin_sessions(active);
CREATE INDEX IF NOT EXISTS idx_activity_logs_user_id ON activity_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_activity_logs_timestamp ON activity_logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_cache_expires ON cache_entries(expires_at);

-- Verify tables were created
\dt
```

### 3. Data Migration Script

```python
#!/usr/bin/env python3
# migrate_phase6.py

import asyncio
import logging
from datetime import datetime
import sqlalchemy as sa

logger = logging.getLogger(__name__)

async def migrate_phase6(database_url: str):
    """
    Migrate existing data for Phase 6 compatibility.
    """
    engine = sa.create_engine(database_url)
    
    try:
        # Step 1: Verify tables exist
        inspector = sa.inspect(engine)
        required_tables = [
            'audit_logs', 'security_alerts', 
            'admin_sessions', 'activity_logs', 'cache_entries'
        ]
        
        for table in required_tables:
            if table not in inspector.get_table_names():
                logger.error(f"Required table missing: {table}")
                return False
        
        logger.info("All required tables exist")
        
        # Step 2: Migrate existing user activity to activity_logs
        with engine.connect() as conn:
            # Existing activity from query_history or similar
            result = conn.execute(
                sa.text("SELECT user_id, query_text, created_at FROM query_history LIMIT 10000")
            )
            
            for row in result:
                conn.execute(
                    sa.text("""
                        INSERT INTO activity_logs (user_id, type, subject_id, timestamp, details)
                        VALUES (:user_id, 'query', :query_id, :timestamp, :details)
                    """),
                    {
                        "user_id": row.user_id,
                        "query_id": None,
                        "timestamp": row.created_at,
                        "details": {"query_text": row.query_text}
                    }
                )
            
            conn.commit()
        
        logger.info("Migration Phase 6 completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        return False

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    success = asyncio.run(migrate_phase6(os.getenv("DATABASE_URL")))
    exit(0 if success else 1)
```

---

## Service Deployment

### 1. Code Deployment

```bash
#!/bin/bash
# deploy.sh

set -e  # Exit on error

DEPLOY_DIR="/opt/agentic-ai-tutor/app"
VENV_DIR="/opt/agentic-ai-tutor/venv"
SERVICE_API="agentic-api"
SERVICE_ADMIN="agentic-admin"

echo "Starting Phase 6 Deployment..."

# 1. Stop services
echo "Stopping services..."
sudo systemctl stop $SERVICE_ADMIN || true
sudo systemctl stop $SERVICE_API || true

# 2. Backup current code
echo "Backing up current code..."
BACKUP_TIME=$(date +%Y%m%d_%H%M%S)
cp -r $DEPLOY_DIR $DEPLOY_DIR.backup.$BACKUP_TIME

# 3. Pull latest code
echo "Deploying new code..."
cd $DEPLOY_DIR
git fetch origin
git checkout production
git pull origin production

# 4. Install/Update dependencies
echo "Installing dependencies..."
$VENV_DIR/bin/pip install -r requirements.txt
$VENV_DIR/bin/pip install -r phase6_requirements.txt

# 5. Run migrations
echo "Running database migrations..."
python migrate_phase6.py

# 6. Collect static files (if needed)
echo "Preparing static files..."
mkdir -p logs

# 7. Start services
echo "Starting services..."
sudo systemctl start $SERVICE_API
sleep 5
sudo systemctl start $SERVICE_ADMIN

# 8. Verify deployment
echo "Verifying deployment..."
bash verify.sh

if [ $? -eq 0 ]; then
    echo "✅ Phase 6 Deployment Successful!"
    exit 0
else
    echo "❌ Deployment verification failed"
    exit 1
fi
```

### 2. Verification Script

```bash
#!/bin/bash
# verify.sh

echo "Verifying Phase 6 Deployment..."

# Check API is running
echo -n "Checking API... "
curl -s http://localhost:8000/docs > /dev/null && echo "✓" || echo "✗"

# Check Admin Dashboard
echo -n "Checking Admin Dashboard... "
curl -s http://localhost:8501/ > /dev/null && echo "✓" || echo "✗"

# Check database connection
echo -n "Checking Database... "
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -d agentic_ai_tutor -c "SELECT 1;" > /dev/null 2>&1 && echo "✓" || echo "✗"

# Check admin tables
echo -n "Checking admin tables... "
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -d agentic_ai_tutor -c "\dt audit_logs" | grep audit_logs > /dev/null && echo "✓" || echo "✗"

# Check logs
echo -n "Checking logs... "
[ -f /var/log/agentic-ai-tutor/app.log ] && echo "✓" || echo "✗"

echo "Verification complete"
```

### 3. Rollback Script

```bash
#!/bin/bash
# rollback.sh

DEPLOY_DIR="/opt/agentic-ai-tutor/app"
SERVICE_API="agentic-api"
SERVICE_ADMIN="agentic-admin"

echo "Rolling back Phase 6 Deployment..."

# Find latest backup
LATEST_BACKUP=$(ls -t $DEPLOY_DIR.backup.* | head -1)

if [ -z "$LATEST_BACKUP" ]; then
    echo "No backup found!"
    exit 1
fi

echo "Using backup: $LATEST_BACKUP"

# Stop services
echo "Stopping services..."
sudo systemctl stop $SERVICE_ADMIN || true
sudo systemctl stop $SERVICE_API || true

# Restore code
echo "Restoring previous version..."
rm -rf $DEPLOY_DIR
mv $LATEST_BACKUP $DEPLOY_DIR

# Restore database (if available)
LATEST_DB_BACKUP=$(ls -t /opt/agentic-ai-tutor/backups/database/*.dump | head -1)
if [ ! -z "$LATEST_DB_BACKUP" ]; then
    echo "Restoring database..."
    pg_restore --clean --if-exists -d agentic_ai_tutor $LATEST_DB_BACKUP
fi

# Start services
echo "Starting services..."
sudo systemctl start $SERVICE_API
sleep 5
sudo systemctl start $SERVICE_ADMIN

echo "✅ Rollback completed"
```

---

## Verification & Testing

### 1. Smoke Tests

```python
#!/usr/bin/env python3
# smoke_tests.py

import requests
import json
import time

BASE_URL = "http://localhost:8000"
ADMIN_TOKEN = "your-admin-token"

def test_api_health():
    """Test API is responding"""
    response = requests.get(f"{BASE_URL}/docs")
    assert response.status_code == 200
    print("✓ API health check passed")

def test_admin_stats():
    """Test admin dashboard stats endpoint"""
    headers = {"Authorization": f"Bearer {ADMIN_TOKEN}"}
    response = requests.get(
        f"{BASE_URL}/admin/dashboard/stats",
        headers=headers
    )
    assert response.status_code == 200
    assert "users" in response.json()
    print("✓ Admin stats endpoint passed")

def test_analytics_endpoint():
    """Test analytics endpoint"""
    headers = {"Authorization": f"Bearer {ADMIN_TOKEN}"}
    response = requests.get(
        f"{BASE_URL}/analytics/user",
        headers=headers
    )
    assert response.status_code == 200
    assert "total_quizzes" in response.json()
    print("✓ Analytics endpoint passed")

def test_database():
    """Test database connection"""
    import sqlalchemy
    engine = sqlalchemy.create_engine(os.getenv("DATABASE_URL"))
    with engine.connect() as conn:
        result = conn.execute(sqlalchemy.text("SELECT 1"))
        assert result.scalar() == 1
    print("✓ Database connection passed")

def run_all_tests():
    """Run all smoke tests"""
    start_time = time.time()
    
    try:
        test_api_health()
        test_database()
        test_admin_stats()
        test_analytics_endpoint()
        
        elapsed = time.time() - start_time
        print(f"\n✅ All smoke tests passed! ({elapsed:.2f}s)")
        return True
    except Exception as e:
        print(f"\n❌ Smoke test failed: {str(e)}")
        return False

if __name__ == "__main__":
    import os
    import sys
    success = run_all_tests()
    sys.exit(0 if success else 1)
```

### 2. Load Testing

```bash
#!/bin/bash
# load_test.sh

# Using Apache Bench
ab -n 1000 -c 10 http://localhost:8000/docs

# Using wrk (if installed)
wrk -t4 -c100 -d30s http://localhost:8000/admin/dashboard/stats

# Monitor during load
watch -n 1 'curl -s http://localhost:8000/admin/dashboard/stats | jq'
```

---

## Post-Deployment

### 1. Monitoring Setup

```yaml
# monitoring_config.yml
services:
  - name: agentic-api
    port: 8000
    health_check: /docs
    alert_on_failure: true

  - name: agentic-admin
    port: 8501
    health_check: /
    alert_on_failure: true

  - name: postgresql
    port: 5432
    alert_on_failure: true

metrics:
  - api_response_time
  - database_query_time
  - cache_hit_ratio
  - error_rate
  - memory_usage
  - disk_usage

alerts:
  - name: api_down
    condition: "health_check fails"
    severity: critical
    action: page_oncall

  - name: slow_queries
    condition: "query_time > 1000ms"
    severity: warning
    action: log_and_notify
```

### 2. Team Notification

```
Subject: Phase 6 Deployment Complete ✅

Team,

Phase 6 (Admin Dashboard & Advanced Analytics) has been successfully deployed to production.

New Features Available:
- ✅ Admin Dashboard (http://your-domain:8501)
- ✅ Advanced Analytics Engine
- ✅ Security Monitoring
- ✅ Audit Logging
- ✅ Analytics APIs

Access:
- Admin Dashboard: Admin users can access via Streamlit
- REST APIs: Available at http://your-domain:8000

Documentation:
- Phase 6 Guide: See PHASE6_GUIDE.md
- API Docs: http://your-domain:8000/docs
- Troubleshooting: See PHASE6_TROUBLESHOOTING.md

Support:
- For issues: Check troubleshooting guide or contact [contact info]
- For questions: Schedule meeting with [team names]

Timeline:
- Deployment started: [time]
- Deployment completed: [time]
- All tests passed: ✅

Team standby continues for 24 hours.

Thanks everyone!
```

### 3. Documentation Update

- [ ] Update README with Phase 6 info
- [ ] Update CHANGELOG
- [ ] Update user documentation
- [ ] Update API documentation
- [ ] Notify stakeholders
- [ ] Schedule training sessions

---

## Monitoring & Maintenance

### Daily Checks

```bash
#!/bin/bash
# daily_check.sh

echo "=== Daily Health Check ==="
echo ""

# Check services
echo "Service Status:"
sudo systemctl status agentic-api
sudo systemctl status agentic-admin

# Check error logs
echo ""
echo "Recent Errors (last 24h):"
grep "ERROR\|CRITICAL" /var/log/agentic-ai-tutor/app.log | tail -5

# Check database
echo ""
echo "Database Status:"
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -d agentic_ai_tutor -c "SELECT 'Database: OK'"

# Check disk space
echo ""
echo "Disk Usage:"
df -h | grep -E "/$|/opt"

# Check memory
echo ""
echo "Memory Usage:"
free -h

# Check backup status
echo ""
echo "Latest Backup:"
ls -lh /opt/agentic-ai-tutor/backups/database/ | tail -1
```

### Weekly Maintenance

```
Monday 02:00 AM:
- [ ] Database maintenance (VACUUM, ANALYZE)
- [ ] Index optimization
- [ ] Log rotation
- [ ] Backup verification
- [ ] Security audit
- [ ] Performance review
```

### Monthly Tasks

```
First Sunday of month 03:00 AM:
- [ ] Full security review
- [ ] Capacity planning
- [ ] Disaster recovery test
- [ ] Policy review
- [ ] Documentation update
- [ ] Team training refresh
```

---

## Success Criteria

✅ **Phase 6 deployment is successful when:**

1. **Functionality**
   - [ ] Admin dashboard accessible
   - [ ] All API endpoints responding
   - [ ] Analytics calculations working
   - [ ] Audit logging capturing events
   - [ ] Security features active

2. **Performance**
   - [ ] API response time < 500ms
   - [ ] Dashboard load time < 5s
   - [ ] Analytics calculation < 2s
   - [ ] No obvious memory leaks

3. **Security**
   - [ ] Admin authentication working
   - [ ] Rate limiting active
   - [ ] Audit trail maintained
   - [ ] No unauthorized access attempts

4. **Data**
   - [ ] All tables populated correctly
   - [ ] Indexes performing well
   - [ ] Backups completed
   - [ ] Data integrity verified

5. **Operations**
   - [ ] Monitoring alerts active
   - [ ] Logging working
   - [ ] Team trained
   - [ ] Documentation complete

---

## Rollback Criteria

🔄 **Consider rollback if:**

- Critical API endpoints fail
- Admin features cause system instability
- Data corruption detected
- Security vulnerability discovered
- Performance degrades significantly (>50%)
- More than 5% error rate

---

## Contact & Escalation

**On-Call Engineer:** [Name] [Phone] [Email]  
**Team Lead:** [Name] [Phone] [Email]  
**CTO:** [Name] [Phone] [Email]  
**Escalation Time:** Immediately for critical issues

---

## Appendix

### A. Environment Checklist
- [ ] All environment variables set
- [ ] No secrets in repository
- [ ] SSL certificates valid
- [ ] Database backups automated

### B. Security Checklist
- [ ] Admin accounts created
- [ ] MFA configured (if required)
- [ ] Rate limiting active
- [ ] Audit logging enabled
- [ ] Access controls verified

### C. Documentation Checklist
- [ ] README updated
- [ ] API docs current
- [ ] Troubleshooting guide available
- [ ] Team trained
- [ ] Runbooks available

---

**Deployment Date:** _______________  
**Deployed By:** _______________  
**Verified By:** _______________  
**Status:** [✅ Success / ❌ Rollback]

---

**For questions or issues, refer to PHASE6_TROUBLESHOOTING.md**
