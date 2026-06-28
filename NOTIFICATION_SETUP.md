# Notification System Setup Guide

The Agentic AI Tutor now includes a comprehensive notification system for sending email and SMS reminders about due topics.

## Features

✅ **Email Notifications**
- Due topics reminder emails with HTML templates
- Weekly performance summary emails
- Customizable notification preferences

✅ **SMS Notifications**
- Due topics summary via SMS (Twilio)
- Concise messages with direct quiz links

✅ **Background Scheduler**
- Automatic daily digest at 8:00 AM
- Weekly performance summary on Sundays at 7:00 PM
- Configurable schedule

## Setup Instructions

### 1. Email Notifications (SMTP)

#### Option A: Gmail

1. Enable 2-Step Verification on your Google Account
2. Generate an App Password:
   - Go to https://myaccount.google.com/apppasswords
   - Select "Mail" and "Windows Computer"
   - Copy the 16-character password

3. Add to your `.env` file:
```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SENDER_EMAIL=your-email@gmail.com
SENDER_PASSWORD=xxxx xxxx xxxx xxxx
```

#### Option B: Other SMTP Providers

Set your SMTP provider credentials:
```env
SMTP_HOST=smtp.provider.com
SMTP_PORT=587
SENDER_EMAIL=your-email@provider.com
SENDER_PASSWORD=your-password
```

### 2. SMS Notifications (Twilio)

1. Create a Twilio account at https://www.twilio.com/console
2. Get your Account SID and Auth Token from the dashboard
3. Get a Twilio phone number
4. Add to your `.env` file:

```env
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=+1234567890
```

### 3. Install Optional Dependencies

Email notifications work with standard Python libraries.
For SMS/scheduler, install optional packages:

```bash
pip install twilio apscheduler
```

## API Endpoints

### Send Notification

**POST** `/notifications/send`

Send a notification to a user about due topics.

```bash
curl -X POST http://localhost:8000/notifications/send \
  -H "Authorization: Bearer YOUR_TOKEN" \
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

### Get Preferences

**GET** `/notifications/preferences`

Get user's notification preferences.

```bash
curl http://localhost:8000/notifications/preferences \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response:**
```json
{
  "email_enabled": true,
  "sms_enabled": false,
  "email_frequency": "daily",
  "sms_frequency": "weekly",
  "quiet_hours_start": "22:00",
  "quiet_hours_end": "08:00"
}
```

### Update Preferences

**POST** `/notifications/preferences`

Update notification preferences.

```bash
curl -X POST http://localhost:8000/notifications/preferences \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email_enabled": true,
    "sms_enabled": true,
    "email_frequency": "weekly"
  }'
```

### Send Weekly Summary

**POST** `/notifications/weekly-summary`

Send performance summary email immediately.

```bash
curl -X POST http://localhost:8000/notifications/weekly-summary \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Background Scheduler

The notification scheduler runs automated tasks:

### Daily Digest (8:00 AM)
- Sends due topics reminder to all active users
- Customizable time via `reschedule_job()`

### Weekly Summary (Sunday 7:00 PM)
- Sends performance summary to all active users
- Shows accuracy by subject and overall progress

### Starting the Scheduler

Add to your application startup:

```python
from src.services.notification_scheduler import NotificationScheduler

scheduler = NotificationScheduler()
scheduler.start()

# Optional: reschedule
scheduler.reschedule_job("daily_digests", hour=7, minute=30)
scheduler.reschedule_job("weekly_summaries", hour=18, minute=0)
```

### Stopping the Scheduler

```python
scheduler.stop()
```

## Email Templates

The system includes professional HTML email templates:

### Due Topics Email
- Topic list with urgency levels
- Current accuracy percentage
- Direct "Quiz Now" buttons
- Dashboard link
- Unsubscribe option

### Performance Summary Email
- Subject-by-subject accuracy breakdown
- Progress visualization
- Total time spent studying
- Link to detailed dashboard

## Customization

### Change Notification Schedule

```python
scheduler.reschedule_job("daily_digests", hour=6, minute=0)  # 6:00 AM
scheduler.reschedule_job("weekly_summaries", hour=17, minute=30)  # 5:30 PM Sundays
```

### Modify Email Templates

Edit templates in `NotificationService.send_due_topics_reminder()` and 
`NotificationService.send_performance_summary()`.

### Filter Recipients

Update `send_daily_digests()` to filter by:
- Activity level
- Preference settings
- Student cohort
- Subject enrolled

```python
users = db.query(User).filter(
    User.is_active == True,
    User.email_notifications_enabled == True
).all()
```

## Troubleshooting

### Email Not Sending

1. Check SMTP credentials in `.env`
2. Verify firewall allows port 587
3. Check sender email is authorized
4. Enable "Less secure app access" (Gmail only)

### SMS Not Sending

1. Verify Twilio account has credit
2. Check Account SID and Auth Token
3. Verify phone number is in E.164 format (+1234567890)
4. Ensure recipient number is valid

### Scheduler Not Running

1. Install APScheduler: `pip install apscheduler`
2. Check server logs for scheduler errors
3. Verify database connection works
4. Ensure scheduler.start() is called

### Database User Not Found

Verify user email exists in database before sending notifications.

## Security Notes

⚠️ **Environment Variables:**
- Never commit `.env` to git
- Store sensitive credentials securely
- Rotate SMTP passwords regularly
- Use API tokens instead of passwords where possible

⚠️ **GDPR/Privacy:**
- Implement unsubscribe links (placeholder in templates)
- Store user consent for emails/SMS
- Provide preference management endpoints
- Allow users to delete their data

## Testing

### Test Email Delivery

```python
from src.services.notification_service import EmailNotificationService

email_service = EmailNotificationService()
success = email_service.send_email(
    "test@example.com",
    "Test Subject",
    "<h1>Test Email</h1><p>This is a test.</p>"
)
print(f"Email sent: {success}")
```

### Test SMS Delivery

```python
from src.services.notification_service import SMSNotificationService

sms_service = SMSNotificationService()
success = sms_service.send_sms(
    "+1234567890",
    "Test message from Agentic AI Tutor"
)
print(f"SMS sent: {success}")
```

### Test Scheduler

```python
from src.services.notification_scheduler import NotificationScheduler

scheduler = NotificationScheduler()
scheduler.start()

# Check job status
status = scheduler.get_job_status("daily_digests")
print(f"Daily digests: {status}")

scheduler.stop()
```

## Next Steps

1. ✅ Configure SMTP credentials in `.env`
2. ✅ (Optional) Set up Twilio for SMS
3. ✅ Test email/SMS delivery
4. ✅ Start notification scheduler
5. ✅ Monitor logs for delivery status
6. ✅ Gather user feedback on notification timing

## Support

For issues or questions:
- Check application logs: `logs/app.log`
- Review error messages in scheduler output
- Test credentials independently (telnet, mail clients)
- Verify database connectivity
