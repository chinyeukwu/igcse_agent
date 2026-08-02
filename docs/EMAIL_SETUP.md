# Email Notification Setup Guide

Complete guide for configuring and testing email notifications in the Agentic AI Tutor.

---

## Quick Start (Gmail)

### Step 1: Generate Gmail App Password

1. Go to https://myaccount.google.com/apppasswords
2. Select **Mail** and **Windows Computer**
3. Google generates a 16-character password
4. Copy the password (without spaces)

### Step 2: Add to .env File

Create or edit `.env` in project root:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SENDER_EMAIL=your-email@gmail.com
SENDER_PASSWORD=xxxx xxxx xxxx xxxx
```

### Step 3: Test Email Sending

```bash
# Test Python script
python test_email.py
```

Expected output:
```
Email test sent successfully to test@example.com
```

---

## Email Providers Setup

### Gmail (Recommended)

**Requirements:**
- Google Account
- 2-Step Verification enabled
- App Password generated

**Configuration:**
```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SENDER_EMAIL=your-email@gmail.com
SENDER_PASSWORD=app-password-16-chars
```

**Troubleshooting:**
- ❌ "Invalid credentials" → Wrong app password format (should be 16 chars)
- ❌ "Account not set up" → Enable 2-Step Verification first
- ❌ "Connection refused" → Port 587 blocked by firewall

---

### Office 365 / Outlook

**Configuration:**
```env
SMTP_HOST=smtp.office365.com
SMTP_PORT=587
SENDER_EMAIL=your-email@outlook.com
SENDER_PASSWORD=your-password
```

**Note:** Requires "Less secure app access" disabled (modern auth only)

---

### SendGrid

**Configuration:**
```env
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SENDER_EMAIL=apikey
SENDER_PASSWORD=SG.your-sendgrid-api-key
```

**Setup:**
1. Create SendGrid account at https://sendgrid.com
2. Generate API key
3. Use `apikey` as username, API key as password

**Advantages:**
- High deliverability
- Webhook support for bounce tracking
- Built-in analytics

---

### Custom SMTP Server

For self-hosted or corporate email:

```env
SMTP_HOST=mail.yourcompany.com
SMTP_PORT=587
SENDER_EMAIL=noreply@yourcompany.com
SENDER_PASSWORD=your-password
```

**Common ports:**
- 25 (plain, unencrypted)
- 587 (STARTTLS, recommended)
- 465 (SSL, legacy)

---

## Testing Email Delivery

### Test 1: Simple Email Send

```python
from src.services.notification_service import EmailNotificationService

email_service = EmailNotificationService()
success = email_service.send_email(
    "your-test-email@gmail.com",
    "Test Subject",
    "<h1>Test Email</h1><p>This is a test from Agentic AI Tutor</p>"
)
print(f"Email sent: {success}")
```

### Test 2: Due Topics Email

```python
from src.services.notification_service import EmailNotificationService

email_service = EmailNotificationService()
due_topics = [
    {"topic": "Trigonometry", "accuracy": 45, "urgency": "HIGH"},
    {"topic": "Calculus", "accuracy": 62, "urgency": "MEDIUM"},
]

success = email_service.send_due_topics_reminder(
    "student@example.com",
    "John Smith",
    due_topics,
    "Maths"
)
print(f"Due topics email sent: {success}")
```

### Test 3: Performance Summary

```python
from src.services.notification_service import EmailNotificationService

email_service = EmailNotificationService()
performance_data = {
    "subjects": {
        "Maths": {"average_score": 78, "quizzes_completed": 5},
        "English": {"average_score": 85, "quizzes_completed": 4},
    },
    "overall_accuracy": 81.5,
    "total_time_minutes": 240,
}

success = email_service.send_performance_summary(
    "student@example.com",
    "John Smith",
    performance_data
)
print(f"Performance summary sent: {success}")
```

---

## API Usage

### Send Notification via API

```bash
curl -X POST http://localhost:8001/notifications/send \
  -H "Authorization: Bearer YOUR_AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "subject": "Maths",
    "notification_type": "email"
  }'
```

**Response:**
```json
{
  "success": true,
  "email_sent": true,
  "sms_sent": false,
  "due_topics_count": 3
}
```

### Get Notification History

```bash
curl http://localhost:8001/notifications/history \
  -H "Authorization: Bearer YOUR_AUTH_TOKEN"
```

**Response:**
```json
{
  "notifications": [
    {
      "id": 1,
      "type": "email",
      "recipient": "student@example.com",
      "subject": "Due Topics Reminder",
      "status": "sent",
      "topic_count": 3,
      "sent_at": "2026-06-28T14:30:00",
      "delivered_at": "2026-06-28T14:30:05",
      "read": false
    }
  ],
  "total": 1,
  "limit": 50,
  "offset": 0
}
```

---

## Email Templates

### Due Topics Email

**Subject:** 📚 Your Maths Topics Are Due for Review

**Content:**
- Greeting with student name
- Table of due topics (5 max)
- Urgency levels (HIGH: red, MEDIUM: orange)
- Current accuracy percentage
- Direct "Quiz Now" buttons
- Link to dashboard
- Unsubscribe option

**Styling:**
- Professional green header (#487A33)
- Responsive design (mobile-friendly)
- Dark mode support via client
- 2-3 minute read time

### Performance Summary Email

**Subject:** 📈 Your Weekly Performance Summary

**Content:**
- Greeting
- Performance by subject table
- Visual accuracy bars
- Overall accuracy percentage
- Total study time
- Call-to-action button
- Trend indicators

---

## Troubleshooting

### Email Not Sending

**Check 1: Credentials**
```python
import os
print(f"SMTP Host: {os.getenv('SMTP_HOST')}")
print(f"SMTP Port: {os.getenv('SMTP_PORT')}")
print(f"Sender Email: {os.getenv('SENDER_EMAIL')}")
# NEVER print password!
```

**Check 2: Connection**
```python
import smtplib
try:
    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    print("Connection successful")
    server.quit()
except Exception as e:
    print(f"Connection failed: {e}")
```

**Check 3: Authentication**
```python
import smtplib
try:
    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login("your-email@gmail.com", "app-password")
    print("Authentication successful")
    server.quit()
except Exception as e:
    print(f"Authentication failed: {e}")
```

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `[Errno 111] Connection refused` | Server/port wrong | Check SMTP_HOST and SMTP_PORT |
| `AuthenticationError` | Wrong password | Regenerate app password for Gmail |
| `SMTPAuthenticationError: 535` | Invalid credentials | Check email and password |
| `timeout` | Firewall blocking | Check if port 587 is open |
| `SSL: CERTIFICATE_VERIFY_FAILED` | TLS issue | Ensure STARTTLS is enabled |

---

## Production Checklist

- [ ] SMTP credentials configured in `.env`
- [ ] Firewall allows outbound SMTP (port 587)
- [ ] Test email sends successfully
- [ ] Notification history tracking working
- [ ] Monitor logs for send failures
- [ ] Set up bounce handling (optional)
- [ ] Document unsubscribe process
- [ ] Backup SMTP provider configured
- [ ] GDPR consent collected
- [ ] Email templates reviewed

---

## Advanced Configuration

### Multiple SMTP Providers (Fallback)

```python
from src.services.notification_service import EmailNotificationService

# Primary
primary = EmailNotificationService(
    smtp_host="smtp.gmail.com",
    sender_email="primary@gmail.com",
    sender_password="app-password"
)

# Fallback
fallback = EmailNotificationService(
    smtp_host="smtp.sendgrid.net",
    sender_email="apikey",
    sender_password="SG.key..."
)

# Try primary, fallback if fails
success = primary.send_email(to, subject, body)
if not success:
    success = fallback.send_email(to, subject, body)
```

### Scheduled Digests

```python
from src.services.notification_scheduler import NotificationScheduler

scheduler = NotificationScheduler()
scheduler.start()

# Runs daily at 8 AM
# Runs weekly Sundays at 7 PM

# Customize times
scheduler.reschedule_job("daily_digests", hour=6, minute=30)
scheduler.reschedule_job("weekly_summaries", hour=18, minute=0)
```

### Bulk Email Sending

```python
from src.services.notification_service import NotificationService
from src.database import get_session
from src.database.models import User

db = get_session()
service = NotificationService()

# Get all users
users = db.query(User).filter(User.is_active == True).all()

# Send to each
for user in users:
    service.send_due_topics_notification(
        db, user.id, user.email,
        student_name=user.username,
        subject="Maths"
    )
```

---

## Security Best Practices

✅ **DO:**
- Store credentials in `.env` (never in code)
- Use app-specific passwords (not main account password)
- Enable 2-Step Verification on email account
- Rotate passwords periodically
- Monitor logs for failed sends
- Use TLS/STARTTLS (port 587)

❌ **DON'T:**
- Commit `.env` to git
- Use main email password
- Store credentials in comments
- Log email addresses unnecessarily
- Send unencrypted passwords
- Use old plaintext SMTP (port 25)

---

## Support

**For issues:**
1. Check email logs: `logs/app.log`
2. Test SMTP connection separately
3. Verify environment variables
4. Check firewall rules
5. Test with official SMTP client

**Email Providers Support:**
- Gmail: https://support.google.com/mail
- Outlook: https://support.microsoft.com/outlook
- SendGrid: https://sendgrid.com/docs

---

## Next Steps

1. ✅ Configure SMTP credentials
2. ✅ Test email sending
3. ✅ Start notification scheduler
4. ✅ Monitor notification history
5. ✅ Set up bounce handling (optional)
6. ✅ Deploy to production
