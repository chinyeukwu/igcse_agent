"""
Notification Service - Sends email and SMS notifications for due topics.
"""

import logging
import os
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session as DBSession

from src.database.models import StudentDifficultyProfile, StudentAnswer, QuizAttempt

logger = logging.getLogger(__name__)


class EmailNotificationService:
    """Handles email notifications via SMTP."""

    def __init__(
        self,
        smtp_host: Optional[str] = None,
        smtp_port: Optional[int] = None,
        sender_email: Optional[str] = None,
        sender_password: Optional[str] = None
    ):
        """Initialize email service with SMTP credentials."""
        self.smtp_host = smtp_host or os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = smtp_port or int(os.getenv("SMTP_PORT", 587))
        self.sender_email = sender_email or os.getenv("SENDER_EMAIL")
        self.sender_password = sender_password or os.getenv("SENDER_PASSWORD")

    def send_email(
        self,
        recipient_email: str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None
    ) -> bool:
        """
        Send email notification.

        Args:
            recipient_email: Recipient's email address
            subject: Email subject
            html_body: HTML content of email
            text_body: Plain text fallback

        Returns:
            True if successful, False otherwise
        """
        try:
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = self.sender_email
            message["To"] = recipient_email

            if text_body:
                message.attach(MIMEText(text_body, "plain"))
            message.attach(MIMEText(html_body, "html"))

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(message)

            logger.info(f"Email sent successfully to {recipient_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {recipient_email}: {str(e)}")
            return False

    def send_due_topics_reminder(
        self,
        recipient_email: str,
        student_name: str,
        due_topics: List[Dict[str, Any]],
        subject: str = "Maths"
    ) -> bool:
        """
        Send due topics reminder email.

        Args:
            recipient_email: Student's email
            student_name: Student's name
            due_topics: List of topics due for review
            subject: Subject name

        Returns:
            True if successful
        """
        # Build HTML email
        topic_rows = ""
        for topic in due_topics[:5]:  # Top 5 due topics
            urgency = topic.get("urgency", "MEDIUM")
            urgency_color = "#DC2626" if urgency == "HIGH" else "#EA580C"
            accuracy = topic.get("accuracy", 0)

            topic_rows += f"""
            <tr style="border-bottom: 1px solid #E5E7EB;">
                <td style="padding: 12px; color: #1F2937;">{topic.get('topic', 'Unknown')}</td>
                <td style="padding: 12px; text-align: center;">
                    <span style="background-color: {urgency_color}; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px;">
                        {urgency}
                    </span>
                </td>
                <td style="padding: 12px; text-align: center; color: #1F2937;">{accuracy:.0f}%</td>
                <td style="padding: 12px; text-align: center;">
                    <a href="https://agentic-ai-tutor.local/quiz?topic={topic.get('topic', '')}"
                       style="color: #487A33; text-decoration: none; font-weight: 500;">Quiz Now</a>
                </td>
            </tr>
            """

        html_body = f"""
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; color: #1F2937; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #487A33; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
                .header h1 {{ margin: 0; font-size: 24px; }}
                .content {{ background-color: #F9FAFB; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
                table {{ width: 100%; border-collapse: collapse; }}
                th {{ background-color: #F3F4F6; padding: 12px; text-align: left; font-weight: 600; color: #1F2937; }}
                .cta-button {{ display: inline-block; background-color: #487A33; color: white; padding: 12px 24px;
                              text-decoration: none; border-radius: 6px; font-weight: 500; margin-top: 10px; }}
                .footer {{ color: #6B7280; font-size: 12px; text-align: center; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📚 Topics Due for Review</h1>
                    <p style="margin: 10px 0 0 0;">Hi {student_name}!</p>
                </div>

                <div class="content">
                    <p>You have <strong>{len(due_topics)}</strong> topics in <strong>{subject}</strong> that are ready for review.</p>
                    <p style="margin-bottom: 15px;">Here are your top priority topics:</p>

                    <table>
                        <thead>
                            <tr style="border-bottom: 2px solid #D1D5DB;">
                                <th>Topic</th>
                                <th style="text-align: center;">Urgency</th>
                                <th style="text-align: center;">Accuracy</th>
                                <th style="text-align: center;">Action</th>
                            </tr>
                        </thead>
                        <tbody>
                            {topic_rows}
                        </tbody>
                    </table>

                    <a href="https://agentic-ai-tutor.local/dashboard" class="cta-button">View Full Dashboard</a>
                </div>

                <div class="footer">
                    <p>This is an automated message from Agentic AI Tutor.
                    <a href="#" style="color: #487A33;">Manage preferences</a></p>
                </div>
            </div>
        </body>
        </html>
        """

        return self.send_email(
            recipient_email,
            f"🎯 Your {subject} Topics Are Due for Review",
            html_body
        )


class SMSNotificationService:
    """Handles SMS notifications via Twilio."""

    def __init__(self, account_sid: Optional[str] = None, auth_token: Optional[str] = None, from_number: Optional[str] = None):
        """Initialize SMS service with Twilio credentials."""
        try:
            from twilio.rest import Client
            self.client = Client(
                account_sid or os.getenv("TWILIO_ACCOUNT_SID"),
                auth_token or os.getenv("TWILIO_AUTH_TOKEN")
            )
            self.from_number = from_number or os.getenv("TWILIO_PHONE_NUMBER")
            self.enabled = True
        except ImportError:
            logger.warning("Twilio not installed. SMS notifications disabled.")
            self.enabled = False

    def send_sms(self, to_number: str, message: str) -> bool:
        """
        Send SMS notification.

        Args:
            to_number: Recipient's phone number (E.164 format)
            message: SMS message content

        Returns:
            True if successful
        """
        if not self.enabled:
            logger.warning("SMS service not enabled")
            return False

        try:
            msg = self.client.messages.create(
                body=message,
                from_=self.from_number,
                to=to_number
            )
            logger.info(f"SMS sent successfully to {to_number}: {msg.sid}")
            return True
        except Exception as e:
            logger.error(f"Failed to send SMS to {to_number}: {str(e)}")
            return False

    def send_due_topics_summary(self, to_number: str, student_name: str, due_topics: List[Dict[str, Any]]) -> bool:
        """
        Send due topics summary via SMS.

        Args:
            to_number: Student's phone number
            student_name: Student's name
            due_topics: List of topics due for review

        Returns:
            True if successful
        """
        if not due_topics:
            return False

        # Build concise SMS message (max 160 chars for standard SMS)
        top_topic = due_topics[0]
        topic_name = top_topic.get("topic", "Unknown")
        urgency = top_topic.get("urgency", "MEDIUM")

        message = f"📚 Hi {student_name}! {topic_name} is due for review ({urgency}). Quiz now: https://aitutor.local/quiz"

        return self.send_sms(to_number, message)


class NotificationPreferences:
    """Manages user notification preferences."""

    PREFERENCE_KEYS = {
        "email_enabled": True,
        "sms_enabled": False,
        "email_frequency": "daily",  # daily, weekly, immediate
        "sms_frequency": "weekly",
        "quiet_hours_start": "22:00",
        "quiet_hours_end": "08:00",
    }

    @staticmethod
    def get_preferences(db: DBSession, user_id: int) -> Dict[str, Any]:
        """
        Get user's notification preferences.
        (In a real system, these would be stored in database)
        """
        return NotificationPreferences.PREFERENCE_KEYS.copy()

    @staticmethod
    def update_preferences(db: DBSession, user_id: int, preferences: Dict[str, Any]) -> bool:
        """
        Update user's notification preferences.
        """
        try:
            # In a real system, update database
            # For now, just validate
            for key in preferences:
                if key not in NotificationPreferences.PREFERENCE_KEYS:
                    logger.warning(f"Unknown preference key: {key}")
            logger.info(f"Updated preferences for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to update preferences: {str(e)}")
            return False


class NotificationService:
    """Main notification orchestrator."""

    def __init__(
        self,
        smtp_host: Optional[str] = None,
        smtp_port: Optional[int] = None,
        sender_email: Optional[str] = None,
        sender_password: Optional[str] = None,
        twilio_account_sid: Optional[str] = None,
        twilio_auth_token: Optional[str] = None,
        twilio_phone_number: Optional[str] = None
    ):
        """Initialize notification service with email and SMS."""
        self.email_service = EmailNotificationService(smtp_host, smtp_port, sender_email, sender_password)
        self.sms_service = SMSNotificationService(twilio_account_sid, twilio_auth_token, twilio_phone_number)

    def send_due_topics_notification(
        self,
        db: DBSession,
        user_id: int,
        recipient_email: str,
        phone_number: Optional[str] = None,
        student_name: str = "Student",
        subject: str = "Maths"
    ) -> Dict[str, bool]:
        """
        Send due topics notification via email and/or SMS.

        Args:
            db: Database session
            user_id: Student ID
            recipient_email: Student's email
            phone_number: Student's phone number (optional)
            student_name: Student's name
            subject: Subject name

        Returns:
            Dict with success status for email and SMS
        """
        # Get due topics from database
        due_topics = self._get_due_topics(db, user_id, subject)

        if not due_topics:
            logger.info(f"No due topics for user {user_id}")
            return {"email": False, "sms": False, "reason": "No due topics"}

        # Get user preferences
        preferences = NotificationPreferences.get_preferences(db, user_id)

        results = {
            "email": False,
            "sms": False,
            "due_topics_count": len(due_topics)
        }

        # Send email if enabled
        if preferences.get("email_enabled"):
            results["email"] = self.email_service.send_due_topics_reminder(
                recipient_email,
                student_name,
                due_topics,
                subject
            )

        # Send SMS if enabled
        if preferences.get("sms_enabled") and phone_number:
            results["sms"] = self.sms_service.send_due_topics_summary(
                phone_number,
                student_name,
                due_topics
            )

        logger.info(f"Notification sent to user {user_id}: email={results['email']}, sms={results['sms']}")
        return results

    def send_performance_summary(
        self,
        recipient_email: str,
        student_name: str,
        performance_data: Dict[str, Any]
    ) -> bool:
        """
        Send weekly performance summary email.

        Args:
            recipient_email: Student's email
            student_name: Student's name
            performance_data: Performance statistics

        Returns:
            True if successful
        """
        subjects_html = ""
        for subject, data in performance_data.get("subjects", {}).items():
            accuracy = data.get("average_score", 0)
            color = "#487A33" if accuracy >= 75 else "#EA580C" if accuracy >= 50 else "#DC2626"

            subjects_html += f"""
            <tr style="border-bottom: 1px solid #E5E7EB;">
                <td style="padding: 12px; color: #1F2937;">{subject}</td>
                <td style="padding: 12px; text-align: center;">
                    <div style="background-color: #F3F4F6; border-radius: 4px; height: 8px; margin-bottom: 4px;">
                        <div style="background-color: {color}; height: 100%; width: {accuracy}%; border-radius: 4px;"></div>
                    </div>
                    <span style="color: {color}; font-weight: 600;">{accuracy:.0f}%</span>
                </td>
                <td style="padding: 12px; text-align: center; color: #6B7280;">{data.get("quizzes_completed", 0)}</td>
            </tr>
            """

        html_body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; color: #1F2937; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #487A33, #64A935); color: white; padding: 30px;
                          border-radius: 8px; margin-bottom: 20px; }}
                .header h1 {{ margin: 0; font-size: 28px; }}
                table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; }}
                th {{ background-color: #F3F4F6; padding: 12px; text-align: left; font-weight: 600; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📈 Your Weekly Performance Summary</h1>
                    <p style="margin: 10px 0 0 0;">Week of {datetime.now().strftime('%B %d, %Y')}</p>
                </div>

                <p>Hi {student_name},</p>
                <p>Here's your performance summary for this week:</p>

                <table>
                    <thead>
                        <tr style="border-bottom: 2px solid #D1D5DB;">
                            <th>Subject</th>
                            <th style="text-align: center;">Accuracy</th>
                            <th style="text-align: center;">Quizzes</th>
                        </tr>
                    </thead>
                    <tbody>
                        {subjects_html}
                    </tbody>
                </table>

                <p><strong>Overall:</strong> {performance_data.get('overall_accuracy', 0):.0f}% average across all subjects</p>
                <p><strong>Total Time:</strong> {performance_data.get('total_time_minutes', 0)} minutes</p>

                <a href="https://agentic-ai-tutor.local/dashboard"
                   style="display: inline-block; background-color: #487A33; color: white; padding: 12px 24px;
                          text-decoration: none; border-radius: 6px; font-weight: 500;">
                    View Detailed Dashboard
                </a>

                <p style="margin-top: 30px; color: #6B7280; font-size: 12px;">
                    Keep up the great work! 🎓
                </p>
            </div>
        </body>
        </html>
        """

        return self.email_service.send_email(
            recipient_email,
            f"📊 Your Weekly Performance Summary",
            html_body
        )

    @staticmethod
    def _get_due_topics(db: DBSession, user_id: int, subject: str) -> List[Dict[str, Any]]:
        """
        Get topics due for review.

        Returns list of topics sorted by urgency.
        """
        # This would call SpacedRepetitionService in real implementation
        # For now, return empty list (would be populated from service)
        from src.services.spaced_repetition_service import SpacedRepetitionService

        return SpacedRepetitionService.get_topics_due_for_review(db, user_id, subject)
