"""
Notification Scheduler - Sends automated notifications at scheduled intervals.
Integrates with APScheduler for background task management.
"""

import logging
from datetime import datetime, time
from typing import Optional, List
from sqlalchemy.orm import Session as DBSession

logger = logging.getLogger(__name__)


class NotificationScheduler:
    """Manages scheduled notification sending."""

    def __init__(self):
        """Initialize scheduler."""
        self.scheduler = None
        self.enabled = False
        try:
            from apscheduler.schedulers.background import BackgroundScheduler
            from apscheduler.triggers.cron import CronTrigger
            self.BackgroundScheduler = BackgroundScheduler
            self.CronTrigger = CronTrigger
            self.enabled = True
        except ImportError:
            logger.warning("APScheduler not installed. Background notifications disabled.")

    def start(self):
        """Start the scheduler."""
        if not self.enabled:
            logger.warning("Scheduler not enabled")
            return False

        try:
            self.scheduler = self.BackgroundScheduler()
            # Schedule daily notification digest at 8 AM
            self.scheduler.add_job(
                self.send_daily_digests,
                self.CronTrigger(hour=8, minute=0),
                id="daily_digests",
                name="Send daily due topics digests"
            )
            # Schedule weekly summary on Sundays at 7 PM
            self.scheduler.add_job(
                self.send_weekly_summaries,
                self.CronTrigger(day_of_week=6, hour=19, minute=0),
                id="weekly_summaries",
                name="Send weekly performance summaries"
            )
            self.scheduler.start()
            logger.info("Notification scheduler started")
            return True
        except Exception as e:
            logger.error(f"Failed to start scheduler: {str(e)}")
            return False

    def stop(self):
        """Stop the scheduler."""
        if self.scheduler:
            self.scheduler.shutdown()
            logger.info("Notification scheduler stopped")

    def send_daily_digests(self, db: Optional[DBSession] = None):
        """
        Send daily digest of due topics to all active users.

        Args:
            db: Database session (optional, will create if not provided)
        """
        if not db:
            from src.database import get_session
            db = get_session()

        try:
            from src.services.notification_service import NotificationService
            from src.database.models import User

            users = db.query(User).filter(User.is_active == True).all()
            logger.info(f"Sending daily digests to {len(users)} users")

            notification_service = NotificationService()

            successful = 0
            failed = 0

            for user in users:
                try:
                    # Get subjects for this user
                    subjects = ["Maths", "English", "Science"]  # Default subjects

                    for subject in subjects:
                        results = notification_service.send_due_topics_notification(
                            db,
                            user_id=user.id,
                            recipient_email=user.email,
                            student_name=user.username,
                            subject=subject
                        )
                        if results.get("email") or results.get("sms"):
                            successful += 1
                        else:
                            failed += 1

                except Exception as e:
                    logger.error(f"Failed to send digest to user {user.id}: {str(e)}")
                    failed += 1

            logger.info(f"Daily digest complete: {successful} sent, {failed} failed")

        except Exception as e:
            logger.error(f"Daily digest job error: {str(e)}")

    def send_weekly_summaries(self, db: Optional[DBSession] = None):
        """
        Send weekly performance summary to all active users.

        Args:
            db: Database session (optional, will create if not provided)
        """
        if not db:
            from src.database import get_session
            db = get_session()

        try:
            from src.services.notification_service import NotificationService
            from src.database.models import User, QuizAttempt

            users = db.query(User).filter(User.is_active == True).all()
            logger.info(f"Sending weekly summaries to {len(users)} users")

            notification_service = NotificationService()

            successful = 0
            failed = 0

            for user in users:
                try:
                    # Get recent quiz data
                    quizzes = db.query(QuizAttempt).filter(
                        QuizAttempt.user_id == user.id
                    ).order_by(QuizAttempt.completed_at.desc()).limit(20).all()

                    if not quizzes:
                        continue

                    # Aggregate by subject
                    subjects = {}
                    for quiz in quizzes:
                        subject = quiz.subject
                        if subject not in subjects:
                            subjects[subject] = {
                                "average_score": 0,
                                "quizzes_completed": 0,
                                "scores": []
                            }
                        subjects[subject]["scores"].append(quiz.score_percentage)
                        subjects[subject]["quizzes_completed"] += 1

                    # Calculate averages
                    for subject in subjects:
                        subjects[subject]["average_score"] = (
                            sum(subjects[subject]["scores"]) / len(subjects[subject]["scores"])
                        )

                    overall_accuracy = (
                        sum(s["average_score"] for s in subjects.values()) / len(subjects)
                        if subjects else 0
                    )

                    performance_data = {
                        "subjects": subjects,
                        "overall_accuracy": overall_accuracy,
                        "total_time_minutes": sum(q.time_taken_seconds for q in quizzes) // 60
                        if quizzes else 0,
                    }

                    # Send email
                    if notification_service.send_performance_summary(
                        user.email,
                        user.username,
                        performance_data
                    ):
                        successful += 1
                    else:
                        failed += 1

                except Exception as e:
                    logger.error(f"Failed to send summary to user {user.id}: {str(e)}")
                    failed += 1

            logger.info(f"Weekly summary complete: {successful} sent, {failed} failed")

        except Exception as e:
            logger.error(f"Weekly summary job error: {str(e)}")

    def reschedule_job(self, job_id: str, hour: int, minute: int = 0) -> bool:
        """
        Reschedule a job to run at a specific time.

        Args:
            job_id: Job ID to reschedule
            hour: Hour (0-23)
            minute: Minute (0-59)

        Returns:
            True if successful
        """
        if not self.scheduler:
            return False

        try:
            job = self.scheduler.get_job(job_id)
            if not job:
                logger.error(f"Job {job_id} not found")
                return False

            self.scheduler.reschedule_job(
                job_id,
                trigger=self.CronTrigger(hour=hour, minute=minute)
            )
            logger.info(f"Rescheduled job {job_id} to {hour:02d}:{minute:02d}")
            return True

        except Exception as e:
            logger.error(f"Failed to reschedule job: {str(e)}")
            return False

    def get_job_status(self, job_id: str) -> Optional[dict]:
        """
        Get status of a scheduled job.

        Args:
            job_id: Job ID

        Returns:
            Job status dictionary or None
        """
        if not self.scheduler:
            return None

        try:
            job = self.scheduler.get_job(job_id)
            if not job:
                return None

            return {
                "id": job.id,
                "name": job.name,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                "enabled": not job.paused,
            }

        except Exception as e:
            logger.error(f"Failed to get job status: {str(e)}")
            return None
