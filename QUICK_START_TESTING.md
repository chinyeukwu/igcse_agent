# Quick Start: Email Delivery Testing

Follow these steps to test email delivery to your Gmail account.

---

## ⚡ Quick Setup (5 minutes)

### Step 1: Generate Gmail App Password (2 min)

1. Go to https://myaccount.google.com/apppasswords
2. Sign in with your Google account
3. Select **Mail** → **Windows Computer**
4. Google generates a 16-character password
5. **Copy the password** (with or without spaces)

Expected format: `xxxx xxxx xxxx xxxx` (16 chars, 4 groups of 4)

---

### Step 2: Create .env File (1 min)

Open PowerShell in the project directory and run:

```powershell
cd C:\projects\agenticaitutor

@"
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SENDER_EMAIL=your-email@gmail.com
SENDER_PASSWORD=xxxx xxxx xxxx xxxx
"@ | Out-File -FilePath ".env" -Encoding UTF8
```

**Replace:**
- `your-email@gmail.com` → Your Gmail address
- `xxxx xxxx xxxx xxxx` → 16-char app password from Step 1

---

### Step 3: Run Test Script (2 min)

```powershell
cd C:\projects\agenticaitutor
.\mytutor\Scripts\python.exe test_email_delivery.py
```

**When prompted:**
```
Enter recipient email address for testing:
  Email: your-email@gmail.com
```

---

## 📊 What the Test Does

The script runs 8 comprehensive tests:

| Test | What It Checks |
|------|-----------------|
| **Test 1** | Environment variables configured |
| **Test 2** | SMTP connection to Gmail server |
| **Test 3** | Gmail authentication |
| **Test 4** | Simple email send |
| **Test 5** | Due topics reminder email |
| **Test 6** | Performance summary email |
| **Test 7** | Notification history database logging |
| **Test 8** | API endpoints responding |

---

## ✅ Expected Output

```
============================================================
                    Test 1: Environment Variables
============================================================

  SMTP_HOST: smtp.gmail.com
  SMTP_PORT: 587
  SENDER_EMAIL: your-email@gmail.com
  SENDER_PASSWORD: SET

  ✓ PASSED - All environment variables configured

============================================================
                    Test 2: SMTP Connection
============================================================

  Connecting to smtp.gmail.com:587...
  Connected successfully!
  Starting TLS encryption...
  TLS enabled!

  ✓ PASSED - SMTP connection successful

============================================================
                    Test 3: SMTP Authentication
============================================================

  Authenticating as your-email@gmail.com...
  Authentication successful!

  ✓ PASSED - SMTP authentication successful

... [more tests] ...

============================================================
                      Test Summary
============================================================

  Tests Passed: 8/8

    ✓ SMTP Connection
    ✓ SMTP Authentication
    ✓ Simple Email
    ✓ Due Topics Email
    ✓ Performance Summary Email
    ✓ Notification History Logging
    ✓ API Endpoints

All tests passed! Email delivery is working correctly.
```

---

## 📧 Emails You'll Receive

After running the test, you should receive 3 professional emails:

### Email 1: Test Email
- Subject: "Test Email from Agentic AI Tutor"
- Content: Confirmation that SMTP is working
- Format: HTML with green header

### Email 2: Due Topics Reminder
- Subject: "Your Maths Topics Are Due for Review"
- Content: Table of 3 sample topics (Trigonometry, Calculus, Algebra)
- Format: Professional HTML with urgency levels

### Email 3: Performance Summary
- Subject: "Your Weekly Performance Summary"
- Content: Performance by subject (Maths, English, Science)
- Format: Professional HTML with progress bars

---

## 🔍 Troubleshooting

### Error: "AuthenticationError" or "Invalid credentials"

**Solution:** App password format is wrong
- Go back to https://myaccount.google.com/apppasswords
- Make sure you're generating for "Mail" and "Windows Computer"
- Copy the exact 16 characters (spaces optional)
- Don't use your main Gmail password

### Error: "Connection refused" or "timeout"

**Solution:** SMTP server unreachable
- Check firewall allows port 587 outbound
- Verify SMTP_HOST is `smtp.gmail.com`
- Try running: `Test-NetConnection smtp.gmail.com -Port 587`

### Error: "Module not found: src"

**Solution:** Run from project root directory
```powershell
cd C:\projects\agenticaitutor
.\mytutor\Scripts\python.exe test_email_delivery.py
```

### Emails not arriving in inbox

**Solution:** Check spam folder
- Gmail sometimes filters new senders
- Move email to "Not Spam" to whitelist
- Try again - future emails should arrive in inbox

---

## 🎯 Next Steps After Testing

### If All Tests Pass ✅

1. **Start the notification scheduler** (sends daily digests at 8 AM)
   ```python
   from src.services.notification_scheduler import NotificationScheduler
   scheduler = NotificationScheduler()
   scheduler.start()
   ```

2. **Test sending notifications via API**
   ```bash
   curl -X POST http://localhost:8001/notifications/send \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -d '{"user_id": 1, "subject": "Maths", "notification_type": "email"}'
   ```

3. **Check notification history**
   ```bash
   curl http://localhost:8001/notifications/history \
     -H "Authorization: Bearer YOUR_TOKEN"
   ```

4. **Deploy to production**
   - Copy .env to production server
   - Start application
   - Monitor logs for email sends

---

## 📚 Files Involved

- **Test Script:** `test_email_delivery.py` (13 KB, 400+ lines)
- **Configuration:** `.env` (created in step 2)
- **Email Service:** `src/services/notification_service.py`
- **Server:** Running on http://127.0.0.1:8001

---

## 💡 Pro Tips

### Tip 1: Multiple Email Tests
You can test sending to different email addresses:
- Test to your main Gmail: `your-email@gmail.com`
- Test to another account: `friend@example.com`
- Test to yourself multiple times to check logs

### Tip 2: Check Email Headers
To verify sender:
1. Open received email in Gmail
2. Click "Show original"
3. Look for "From:" header
4. Should show: `your-email@gmail.com`

### Tip 3: Monitor Logs
During test, check application logs:
```bash
tail -f logs/app.log | grep -i "notification\|email"
```

---

## ✨ Success Checklist

After completing all steps:

- [ ] Generated Gmail app password
- [ ] Created .env file with credentials
- [ ] Ran test script successfully
- [ ] All 8 tests passed
- [ ] Received 3 test emails
- [ ] Verified emails in inbox
- [ ] Ready for production deployment

---

## Support

**Problem:** Something went wrong  
**Solution:** Check these in order:
1. App password correct (16 chars)
2. SMTP_HOST is `smtp.gmail.com`
3. Firewall allows port 587
4. Running from project root directory
5. Server is running on 127.0.0.1:8001

See `EMAIL_SETUP.md` for more detailed troubleshooting.

---

**Ready to test? Follow the Quick Setup above! 🚀**
