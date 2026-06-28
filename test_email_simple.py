#!/usr/bin/env python3
"""
Simple Email Test - Non-interactive version
Just tests SMTP connection and sends one email
"""

import os
import sys
import smtplib
from pathlib import Path

# Color codes
GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"
BOLD = "\033[1m"

# Set up path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load .env file
def load_env_file():
    """Load .env file into environment variables"""
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        with open(env_path, 'r', encoding='utf-8-sig') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()
        return True
    return False

# Load environment
if not load_env_file():
    print(f"{RED}ERROR: .env file not found!{RESET}")
    sys.exit(1)

from src.services.notification_service import EmailNotificationService

# Get credentials
smtp_host = os.getenv("SMTP_HOST")
smtp_port = os.getenv("SMTP_PORT")
sender_email = os.getenv("SENDER_EMAIL")
sender_password = os.getenv("SENDER_PASSWORD")
recipient_email = os.getenv("SENDER_EMAIL")  # Send to self

print(f"\n{BOLD}Email Delivery Test{RESET}\n")
print(f"SMTP Host: {smtp_host}")
print(f"Sender: {sender_email}")
print(f"Recipient: {recipient_email}\n")

# Test 1: SMTP Connection
print(f"{BOLD}Test 1: SMTP Connection{RESET}")
try:
    server = smtplib.SMTP(smtp_host, int(smtp_port), timeout=5)
    server.starttls()
    print(f"{GREEN}[PASS]{RESET} Connected to SMTP server\n")
    server.quit()
except Exception as e:
    print(f"{RED}[FAIL]{RESET} {str(e)}\n")
    sys.exit(1)

# Test 2: Authentication
print(f"{BOLD}Test 2: SMTP Authentication{RESET}")
try:
    server = smtplib.SMTP(smtp_host, int(smtp_port), timeout=5)
    server.starttls()
    server.login(sender_email, sender_password)
    print(f"{GREEN}[PASS]{RESET} Authenticated successfully\n")
    server.quit()
except Exception as e:
    print(f"{RED}[FAIL]{RESET} {str(e)}\n")
    sys.exit(1)

# Test 3: Send Email
print(f"{BOLD}Test 3: Send Test Email{RESET}")
try:
    email_service = EmailNotificationService()
    success = email_service.send_email(
        recipient_email,
        "Test Email from Agentic AI Tutor",
        """
        <html>
        <body style="font-family: Arial, sans-serif; background-color: #f9fafb; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto;">
                <div style="background-color: #487A33; color: white; padding: 20px; border-radius: 8px;">
                    <h1 style="margin: 0;">Test Email Successful!</h1>
                </div>
                <div style="background-color: white; padding: 20px; border: 1px solid #e5e7eb; border-radius: 8px; margin-top: 20px;">
                    <p>This is a test email from the Agentic AI Tutor.</p>
                    <p><strong>Status:</strong> Email delivery is working correctly!</p>
                    <p><strong>Next Steps:</strong></p>
                    <ul>
                        <li>Configure notification preferences in the dashboard</li>
                        <li>Enable email notifications for due topics</li>
                        <li>Start the notification scheduler</li>
                    </ul>
                </div>
            </div>
        </body>
        </html>
        """
    )

    if success:
        print(f"{GREEN}[PASS]{RESET} Email sent successfully")
        print(f"\n{GREEN}All tests passed! Check your inbox.{RESET}\n")
    else:
        print(f"{RED}[FAIL]{RESET} Failed to send email\n")
        sys.exit(1)

except Exception as e:
    print(f"{RED}[FAIL]{RESET} {str(e)}\n")
    sys.exit(1)
