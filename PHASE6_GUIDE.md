# Phase 6: Admin Dashboard & Advanced Analytics - Implementation Guide

## Overview
Phase 6 brings enterprise-grade admin capabilities and sophisticated analytics to the Agentic AI Tutor platform. This phase includes a comprehensive admin dashboard, advanced analytics engine, and real-time monitoring features.

## Components Implemented

### 1. Admin Dashboard (`src/frontend/admin_dashboard.py`)
**Purpose:** Centralized interface for administrators to manage the platform

#### Features:
- **System Overview**
  - Real-time metrics (active users, quizzes, sessions, alerts)
  - Quick statistics dashboard
  - System health indicators

- **User Management**
  - View all registered users with pagination
  - Search and detailed user profiles
  - User statistics (quizzes completed, average score)
  - Administrative actions (enable, disable, reset password, deactivate)
  - Recent activity tracking

- **Security Monitoring**
  - Real-time security alerts
  - Injection attack detection
  - Critical alerts highlighting
  - Audit log tracking
  - Alert severity categorization (high, medium, low)

- **System Statistics**
  - Cache performance metrics
  - Database statistics
  - Resource cleanup utilities
  - Usage trends

- **Configuration**
  - Retention policies
  - Security settings
  - Session management
  - MFA configuration

#### Usage:
```python
from src.frontend.admin_dashboard import render_admin_dashboard

# In Streamlit app
render_admin_dashboard(token=auth_token, username=username)
```

### 2. Advanced Analytics Engine (`src/analytics/advanced_analytics.py`)
**Purpose:** Sophisticated data analysis and insight generation

#### Key Classes:

**AnalyticsEngine**
- Trend detection and prediction
- Anomaly detection
- Statistical analysis
- Learning pattern recognition
- Insight generation
- Performance analysis

#### Major Methods:

```python
engine = AnalyticsEngine()

# Trend Analysis
trend = engine.detect_trend(
    data_points=[(datetime, value), ...],
    window_size=7
)
# Returns: Trend with direction, slope, strength

# Anomaly Detection
anomalies = engine.detect_anomalies(
    data_points=[scores],
    method="zscore",  # or "iqr"
    threshold=2.0
)

# Statistical Analysis
stats = engine.calculate_statistics(data_points)
# Returns: count, mean, median, std_dev, variance, min, max, q1, q3

# Quiz Performance Analysis
analysis = engine.analyze_quiz_performance(
    quiz_scores=[85, 90, 78, 92],
    quiz_times=[45, 38, 52, 40],
    time_unit="minutes"
)

# Learning Patterns
patterns = engine.analyze_learning_patterns(activity_log)
# Returns: hourly/daily distribution, peak times, activity breakdown

# Insights Generation
insights = engine.generate_insights(
    quiz_data={"scores": [...]},
    user_profile={...},
    activity_log=[...]
)

# Performance Prediction
predictions = engine.predict_performance(
    historical_scores=[...],
    future_periods=5
)
```

#### Data Models:

**Trend**
```python
@dataclass
class Trend:
    direction: TrendDirection  # uptrend, downtrend, stable
    slope: float               # Rate of change
    strength: float            # 0-1, statistical significance
    start_date: datetime
    end_date: datetime
    predicted_value: Optional[float]
```

**Insight**
```python
@dataclass
class Insight:
    title: str                 # e.g., "Excellent Performance"
    description: str           # Detailed description
    impact: str                # "high", "medium", "low"
    category: str              # "performance", "behavior", "security", "usage"
    data_point: Optional[float]
    recommendation: Optional[str]
```

### 3. Analytics Dashboard UI (`src/frontend/analytics_dashboard.py`)
**Purpose:** Visualization and exploration of analytics

#### Views:

**Overview Tab**
- Total quizzes attempted
- Average score
- Study time
- Current streak
- Score distribution histogram
- Recent activity feed

**Performance Tab**
- Score progression over time
- Highest/lowest scores
- Efficiency metrics
- Time analysis
- Improvement trend indicator
- Performance trend visualization

**Learning Patterns Tab**
- Activity by hour of day
- Activity by day of week
- Activity type breakdown (pie chart)
- Peak activity identification
- Pattern summaries

**Predictions Tab**
- Future performance forecasts
- Confidence intervals
- Trend extrapolation
- Prediction details table
- Historical + predicted visualization

**Insights Tab**
- AI-generated insights
- Categorized by impact level
- Filter by category
- Recommendations
- Data-driven suggestions

#### Usage:
```python
# Start analytics dashboard
streamlit run src/frontend/analytics_dashboard.py
```

### 4. Admin & Analytics API Routes (`src/api/admin_analytics_routes.py`)
**Purpose:** RESTful endpoints for admin and analytics operations

#### Admin Routes:

```
GET    /admin/dashboard/stats          - Dashboard statistics
GET    /admin/users                    - All users (paginated)
GET    /admin/user/{user_id}           - User details
POST   /admin/user/{user_id}/action    - Perform user action
GET    /admin/security-alerts          - Security alerts
GET    /admin/dashboard/usage          - System usage stats
POST   /admin/cleanup                  - Clean up resources
```

#### Analytics Routes:

```
GET    /analytics/user                 - User analytics
GET    /analytics/performance          - Performance analytics
GET    /analytics/learning-patterns    - Learning patterns
GET    /analytics/user/quiz-scores     - Quiz scores
GET    /analytics/insights             - AI insights
POST   /analytics/export-report        - Export report
GET    /analytics/trends               - Trend analysis
GET    /analytics/anomalies            - Anomaly detection
```

#### Example API Calls:

```python
import requests

token = "admin_token"
headers = {"Authorization": f"Bearer {token}"}

# Get dashboard stats
response = requests.get(
    "http://localhost:8000/admin/dashboard/stats",
    headers=headers
)
stats = response.json()

# Analyze user performance
response = requests.get(
    "http://localhost:8000/analytics/performance",
    headers=headers
)
perf_data = response.json()

# Get AI insights
response = requests.get(
    "http://localhost:8000/analytics/insights",
    headers=headers
)
insights = response.json()

# Detect trends
response = requests.get(
    "http://localhost:8000/analytics/trends",
    params={
        "metric": "quiz_scores",
        "window_size": 7
    },
    headers=headers
)
trend = response.json()
```

### 5. Security Utilities (`src/tools/security_utils.py`)
**Purpose:** Comprehensive security management

#### Key Components:

**TokenManager**
- JWT token creation and verification
- Admin token generation
- Token expiration handling
- Token type validation

**RateLimiter**
- Failed login attempt tracking
- Automatic lockout mechanism
- Configurable limits and durations

**AuditLogger**
- Admin action logging
- Security event tracking
- Detailed audit trails
- Severity classification

**PermissionValidator**
- Admin role verification
- Account status validation
- Data ownership checks

**PasswordValidator**
- Strength requirements
- Complexity validation
- Format checking

**MFAHandler**
- MFA code generation
- Code verification
- Optional multi-factor authentication

**SessionManager**
- Active session tracking
- IP address validation
- Session timeout management
- Automatic cleanup

#### Configuration:

```python
class SecurityConfig:
    SECRET_KEY = "change-in-production"
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 30
    REFRESH_TOKEN_EXPIRE_DAYS = 7
    MAX_LOGIN_ATTEMPTS = 5
    LOCKOUT_DURATION_MINUTES = 15
    REQUIRE_MFA_FOR_ADMIN = True
    ADMIN_SESSION_TIMEOUT_MINUTES = 60
```

#### Usage:

```python
from src.tools.security_utils import (
    TokenManager, AuditLogger, PermissionValidator, 
    SessionManager, rate_limiter, SecurityConfig
)

# Create admin token
token = TokenManager.create_admin_token(
    user_id=1,
    username="admin"
)

# Verify token
payload = TokenManager.verify_token(token)

# Log admin action
await AuditLogger.log_admin_action(
    admin_id=1,
    action="user_deactivate",
    resource="user_123",
    details={"reason": "Violation"}
)

# Manage rate limiting
if rate_limiter.is_rate_limited("user@email.com"):
    # Handle rate limit exceeded

rate_limiter.record_attempt("user@email.com")
rate_limiter.reset_attempts("user@email.com")

# Validate permissions
PermissionValidator.require_admin(user)
PermissionValidator.require_active(user)
```

## Integration with Main Application

### 1. Update Main FastAPI App

```python
# src/main.py
from fastapi import FastAPI
from src.api.admin_analytics_routes import (
    get_admin_routes,
    get_analytics_routes
)

app = FastAPI()

# Include routers
app.include_router(get_admin_routes())
app.include_router(get_analytics_routes())
```

### 2. Database Requirements

The implementation expects following database methods:
- `get_users_paginated(skip, limit)`
- `count_users()`
- `count_active_users()`
- `get_user_quiz_attempts(user_id, since_date)`
- `get_user_quiz_stats(user_id)`
- `get_user_activity(user_id, limit)`
- `calculate_user_streak(user_id)`
- `get_security_alerts(limit)`
- `get_cache_stats()`
- `get_database_stats()`
- `cleanup_resources(resource_type, older_than_days)`
- `log_audit(action, details)`

Implement these methods in your database layer.

### 3. Streamlit App Integration

```python
# src/frontend/chatbot_streamlit.py
import streamlit as st
from src.frontend.admin_dashboard import render_admin_dashboard
from src.frontend.analytics_dashboard import render_analytics_dashboard

# Add navigation
page = st.sidebar.radio("Select Page", [
    "Chat",
    "Analytics",
    "Admin Dashboard"
])

if page == "Chat":
    # Existing chat functionality
    pass
elif page == "Analytics":
    render_analytics_dashboard()
elif page == "Admin Dashboard":
    render_admin_dashboard(token, username)
```

## Advanced Features

### 1. Anomaly Detection

Detects unusual patterns in quiz performance:
- Z-score method for normally distributed data
- IQR method for skewed distributions
- Configurable sensitivity thresholds

### 2. Trend Prediction

Linear regression-based forecasting:
- Calculates confidence intervals
- Estimates future performance
- Statistical significance testing

### 3. Learning Pattern Analysis

Identifies optimal study times:
- Peak activity hours
- Most productive days
- Activity type distribution
- Time-based recommendations

### 4. Performance Insights

AI-generated insights include:
- Performance metrics
- Progress tracking
- Behavioral patterns
- Actionable recommendations

## Security Best Practices

1. **Token Management**
   - Change SECRET_KEY in production
   - Use HTTPS only
   - Implement token refresh logic

2. **Admin Sessions**
   - Enable MFA for admin accounts
   - Track admin actions in audit logs
   - Implement session timeouts
   - Validate IP addresses

3. **Rate Limiting**
   - Prevent brute force attacks
   - Track failed login attempts
   - Automatic lockout after max attempts

4. **Data Privacy**
   - Only admins can access user data
   - Audit all data access
   - Implement data retention policies
   - Secure cleanup of old data

5. **Anomaly Detection**
   - Monitor for injection attacks
   - Track unusual access patterns
   - Alert on suspicious activities

## Configuration & Deployment

### Environment Variables
```
ADMIN_SECRET_KEY=your-secret-key
DATABASE_URL=postgresql://...
CACHE_REDIS_URL=redis://localhost:6379
LOG_LEVEL=INFO
ENABLE_MFA=true
SESSION_TIMEOUT_MINUTES=60
```

### Docker Deployment
```dockerfile
FROM python:3.11
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "src/main.py"]
```

## Monitoring & Maintenance

### Key Metrics to Monitor
- Active user count
- Average quiz scores
- System response times
- Security alert frequency
- Cache hit rates
- Database query performance

### Maintenance Tasks
- Regular backups of audit logs
- Cleanup of expired sessions
- Cache optimization
- Database index maintenance
- Log rotation

## Performance Optimization

1. **Caching**
   - Cache dashboard stats (5-minute TTL)
   - Cache user activity summaries
   - Cache analytics calculations

2. **Database Queries**
   - Use appropriate indexes
   - Implement pagination
   - Batch operations where possible

3. **Real-time Updates**
   - Use WebSockets for live alerts
   - Implement delta updates
   - Reduce polling frequency

## Testing

### Unit Tests
```python
from src.analytics.advanced_analytics import AnalyticsEngine

def test_trend_detection():
    engine = AnalyticsEngine()
    data = [(datetime(2024, 1, i), 70 + i) for i in range(10)]
    trend = engine.detect_trend(data)
    assert trend.direction == TrendDirection.UPTREND

def test_anomaly_detection():
    engine = AnalyticsEngine()
    data = [70, 72, 71, 73, 100]  # 100 is anomaly
    anomalies = engine.detect_anomalies(data)
    assert len(anomalies) > 0
```

### Integration Tests
```python
def test_admin_dashboard_access():
    # Test admin authentication
    # Test data retrieval
    # Test UI rendering
```

## Troubleshooting

### Common Issues

1. **Admin Login Fails**
   - Check token validity
   - Verify admin role in database
   - Check rate limiting status

2. **Analytics Not Loading**
   - Verify database connection
   - Check data availability
   - Review error logs

3. **Performance Issues**
   - Check cache status
   - Review query performance
   - Optimize database indexes

## Future Enhancements

1. **Interactive Dashboards**
   - Real-time WebSocket updates
   - Drag-and-drop widget customization
   - Custom alert thresholds

2. **Advanced Analytics**
   - Machine learning-based predictions
   - Clustering analysis
   - Natural language insights

3. **Multi-user Support**
   - Role-based access control (RBAC)
   - Department-level analytics
   - Granular permission management

4. **Export & Reporting**
   - PDF report generation
   - Scheduled email reports
   - Data export to external systems

5. **Mobile Support**
   - Responsive admin interface
   - Mobile app for alerts
   - Push notifications

## References

- FastAPI Documentation: https://fastapi.tiangolo.com
- Streamlit Documentation: https://docs.streamlit.io
- SciPy Statistics: https://docs.scipy.org/doc/sci py/reference/stats.html
- JWT Tokens: https://jwt.io

---

**Phase 6 Status:** ✅ Complete
- Admin Dashboard: Fully implemented
- Advanced Analytics: Fully implemented
- Security: Comprehensive security layer
- API: Complete REST endpoints
- UI: Full Streamlit integration
