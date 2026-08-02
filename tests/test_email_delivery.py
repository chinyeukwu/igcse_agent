#!/usr/bin/env python3
"""
Comprehensive Email Delivery Test Script
Tests SMTP connection, authentication, and email sending
"""

import os
import sys
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

# Color codes for output (defined early so functions can use them)
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"

# Set up path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load .env file
def load_env_file():
    """Load .env file into environment variables"""
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        print(f"  Loading .env file from {env_path}...")
        # Use utf-8-sig to handle BOM (Byte Order Mark)
        with open(env_path, 'r', encoding='utf-8-sig') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    os.environ[key] = value
        print(f"  .env file loaded successfully!")
        print(f"  SMTP_HOST: {os.getenv('SMTP_HOST')}")
        print(f"  SENDER_EMAIL: {os.getenv('SENDER_EMAIL')}\n")
    else:
        print(f"  Warning: .env file not found at {env_path}\n")

# Load environment variables from .env before importing services
load_env_file()

from src.services.notification_service import EmailNotificationService
from src.database import get_session
from src.database.models import User


def print_header(title):
    """Print formatted section header"""
    print(f"\n{BOLD}{BLUE}{'='*60}{RESET}")
    print(f"{BOLD}{BLUE}{title:^60}{RESET}")
    print(f"{BOLD}{BLUE}{'='*60}{RESET}\n")


def print_test(name, passed, message=""):
    """Print test result"""
    # Use ASCII characters instead of Unicode to avoid encoding issues
    check = "[PASS]" if passed else "[FAIL]"
    color = GREEN if passed else RED
    status = f"{color}{check}{RESET}"
    print(f"  {status} - {name}")
    if message:
        print(f"          {message}")


def test_environment_variables():
    """Test 1: Check if SMTP credentials are configured"""
    print_header("Test 1: Environment Variables")

    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = os.getenv("SMTP_PORT")
    sender_email = os.getenv("SENDER_EMAIL")
    sender_password = os.getenv("SENDER_PASSWORD")

    print(f"  SMTP_HOST: {smtp_host or 'NOT SET'}")
    print(f"  SMTP_PORT: {smtp_port or 'NOT SET'}")
    print(f"  SENDER_EMAIL: {sender_email or 'NOT SET'}")
    print(f"  SENDER_PASSWORD: {'SET' if sender_password else 'NOT SET'}\n")

    all_set = smtp_host and smtp_port and sender_email and sender_password

    print_test(
        "All environment variables configured",
        all_set,
        "Configure in .env file if missing"
    )

    return smtp_host, smtp_port, sender_email, sender_password


def test_smtp_connection(smtp_host, smtp_port):
    """Test 2: SMTP server connection"""
    print_header("Test 2: SMTP Connection")

    try:
        print(f"  Connecting to {smtp_host}:{smtp_port}...")
        server = smtplib.SMTP(smtp_host, int(smtp_port), timeout=5)
        print(f"  Connected successfully!")

        print(f"  Starting TLS encryption...")
        server.starttls()
        print(f"  TLS enabled!")

        server.quit()
        print_test("SMTP connection successful", True)
        return True

    except Exception as e:
        print_test("SMTP connection successful", False, str(e))
        return False


def test_authentication(smtp_host, smtp_port, sender_email, sender_password):
    """Test 3: SMTP authentication"""
    print_header("Test 3: SMTP Authentication")

    try:
        print(f"  Authenticating as {sender_email}...")
        server = smtplib.SMTP(smtp_host, int(smtp_port), timeout=5)
        server.starttls()
        server.login(sender_email, sender_password)
        print(f"  Authentication successful!")

        server.quit()
        print_test("SMTP authentication successful", True)
        return True

    except smtplib.SMTPAuthenticationError as e:
        print_test("SMTP authentication successful", False, f"Invalid credentials: {e}")
        return False
    except Exception as e:
        print_test("SMTP authentication successful", False, str(e))
        return False


def test_simple_email(recipient_email):
    """Test 4: Send simple test email"""
    print_header("Test 4: Simple Email Send")

    try:
        print(f"  Recipient: {recipient_email}")
        print(f"  Subject: Test Email from Agentic AI Tutor")
        print(f"  Sending...")

        email_service = EmailNotificationService()
        success = email_service.send_email(
            recipient_email,
            "Test Email from Agentic AI Tutor",
            """
            <html>
            <head>
                <style>
                    body { font-family: Arial, sans-serif; }
                    .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                    .header { background-color: #487A33; color: white; padding: 20px; border-radius: 8px; }
                    .content { background-color: #f9fafb; padding: 20px; margin-top: 20px; border-radius: 8px; }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Test Email Successful!</h1>
                    </div>
                    <div class="content">
                        <p>This is a test email from the Agentic AI Tutor.</p>
                        <p><strong>Test completed at:</strong> """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """</p>
                        <p>If you received this email, your SMTP configuration is working correctly!</p>
                        <p><strong>Next steps:</strong></p>
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

        print_test("Simple email send", success, f"Email delivered: {success}")
        return success

    except Exception as e:
        print_test("Simple email send", False, str(e))
        return False


def test_due_topics_email(recipient_email):
    """Test 5: Send due topics reminder email"""
    print_header("Test 5: Due Topics Email")

    try:
        print(f"  Recipient: {recipient_email}")
        print(f"  Subject: Due Topics Reminder")
        print(f"  Sending...")

        due_topics = [
            {"topic": "Trigonometry", "accuracy": 45, "urgency": "HIGH"},
            {"topic": "Calculus", "accuracy": 62, "urgency": "MEDIUM"},
            {"topic": "Algebra", "accuracy": 38, "urgency": "HIGH"},
        ]

        email_service = EmailNotificationService()
        success = email_service.send_due_topics_reminder(
            recipient_email,
            "Test Student",
            due_topics,
            "Maths"
        )

        print_test("Due topics email send", success, f"Email delivered: {success}")
        return success

    except Exception as e:
        print_test("Due topics email send", False, str(e))
        return False


def test_performance_summary_email(recipient_email):
    """Test 6: Send performance summary email"""
    print_header("Test 6: Performance Summary Email")

    try:
        print(f"  Recipient: {recipient_email}")
        print(f"  Subject: Weekly Performance Summary")
        print(f"  Sending...")

        performance_data = {
            "subjects": {
                "Maths": {"average_score": 78, "quizzes_completed": 5},
                "English": {"average_score": 85, "quizzes_completed": 4},
                "Science": {"average_score": 72, "quizzes_completed": 3},
            },
            "overall_accuracy": 78.3,
            "total_time_minutes": 240,
        }

        email_service = EmailNotificationService()
        success = email_service.send_performance_summary(
            recipient_email,
            "Test Student",
            performance_data
        )

        print_test("Performance summary email send", success, f"Email delivered: {success}")
        return success

    except Exception as e:
        print_test("Performance summary email send", False, str(e))
        return False


def test_notification_history_logging():
    """Test 7: Notification history database logging"""
    print_header("Test 7: Notification History Logging")

    try:
        print(f"  Checking notification history table...")

        db = get_session()

        # Count notifications
        from src.database.models import NotificationHistory
        count = db.query(NotificationHistory).count()

        print(f"  Total notifications in database: {count}")

        # Get recent notifications
        recent = db.query(NotificationHistory).order_by(
            NotificationHistory.created_at.desc()
        ).limit(3).all()

        print(f"  Recent notifications:")
        for notif in recent:
            print(f"    - {notif.notification_type} to {notif.recipient} ({notif.status})")

        print_test("Notification history logging", True, f"Found {count} notifications")
        return True

    except Exception as e:
        print_test("Notification history logging", False, str(e))
        return False


def test_api_endpoints():
    """Test 8: Notification API endpoints"""
    print_header("Test 8: API Endpoints")

    try:
        import requests
        from requests.exceptions import ConnectionError

        base_url = "http://127.0.0.1:8001"
        endpoints = [
            ("GET", "/health"),
            ("GET", "/notifications/history"),
            ("GET", "/notifications/stats"),
        ]

        print(f"  Testing endpoints at {base_url}...\n")

        for method, endpoint in endpoints:
            try:
                url = f"{base_url}{endpoint}"
                if method == "GET":
                    response = requests.get(url, timeout=2)
                    status = response.status_code
                    passed = status in [200, 401, 403]  # 401/403 ok if auth required
                    print_test(f"{method} {endpoint}", passed, f"Status: {status}")

            except ConnectionError:
                print_test(f"{method} {endpoint}", False, "Server not running on port 8001")
            except Exception as e:
                print_test(f"{method} {endpoint}", False, str(e))

    except ImportError:
        print(f"  {YELLOW}Note: requests library not installed, skipping API tests{RESET}")
        print(f"  Install with: pip install requests")


def main():
    """Run all email delivery tests"""
    print(f"\n{BOLD}{BLUE}AGENTIC AI TUTOR - EMAIL DELIVERY TEST SUITE{RESET}")
    print(f"{BOLD}{BLUE}Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{RESET}\n")

    # Get SMTP credentials
    smtp_host, smtp_port, sender_email, sender_password = test_environment_variables()

    if not all([smtp_host, smtp_port, sender_email, sender_password]):
        print(f"\n{RED}ERROR: Missing SMTP configuration!{RESET}")
        print(f"Create .env file with:")
        print(f"  SMTP_HOST=smtp.gmail.com")
        print(f"  SMTP_PORT=587")
        print(f"  SENDER_EMAIL=your-email@gmail.com")
        print(f"  SENDER_PASSWORD=your-app-password")
        return

    # Get recipient email
    print(f"\n{BOLD}Enter recipient email address for testing:{RESET}")
    recipient_email = input(f"  Email: ").strip()

    if not recipient_email or "@" not in recipient_email:
        print(f"\n{RED}ERROR: Invalid email address!{RESET}")
        return

    # Run tests
    results = []

    if test_smtp_connection(smtp_host, smtp_port):
        results.append(("SMTP Connection", True))

        if test_authentication(smtp_host, smtp_port, sender_email, sender_password):
            results.append(("SMTP Authentication", True))

            # Send test emails
            if test_simple_email(recipient_email):
                results.append(("Simple Email", True))
            else:
                results.append(("Simple Email", False))

            if test_due_topics_email(recipient_email):
                results.append(("Due Topics Email", True))
            else:
                results.append(("Due Topics Email", False))

            if test_performance_summary_email(recipient_email):
                results.append(("Performance Summary Email", True))
            else:
                results.append(("Performance Summary Email", False))

        else:
            results.append(("SMTP Authentication", False))

    else:
        results.append(("SMTP Connection", False))

    # Test database logging
    test_notification_history_logging()

    # Test API endpoints
    test_api_endpoints()

    # Summary
    print_header("Test Summary")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    print(f"  Tests Passed: {GREEN}{passed}/{total}{RESET}\n")

    for test_name, result in results:
        status = f"{GREEN}✓{RESET}" if result else f"{RED}✗{RESET}"
        print(f"    {status} {test_name}")

    print(f"\n{BOLD}Ended at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{RESET}\n")

    if passed == total:
        print(f"{GREEN}{BOLD}All tests passed! Email delivery is working correctly.{RESET}\n")
    else:
        print(f"{RED}{BOLD}Some tests failed. Check configuration and try again.{RESET}\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Test interrupted by user.{RESET}\n")
    except Exception as e:
        print(f"\n{RED}Unexpected error: {e}{RESET}\n")
