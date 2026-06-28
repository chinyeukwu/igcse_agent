"""
Spaced Repetition & Topic Performance Service
Identifies weak topics and optimizes quiz scheduling using spaced repetition.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session as DBSession

from src.database.models import StudentAnswer, QuizAttempt

logger = logging.getLogger(__name__)


class TopicPerformanceService:
    """Analyzes topic-level performance and identifies weak areas."""

    @staticmethod
    def extract_topics_from_questions(questions: List[Dict[str, Any]]) -> List[str]:
        """Extract topics from question text (heuristic-based)."""
        topics = []

        keyword_mapping = {
            # Maths topics
            "algebra": ["solve", "equation", "polynomial", "x =", "expand"],
            "geometry": ["angle", "triangle", "circle", "area", "perimeter", "shape"],
            "trigonometry": ["sin", "cos", "tan", "radian", "degree"],
            "calculus": ["derivative", "integral", "limit", "differential"],
            "statistics": ["mean", "median", "standard deviation", "histogram", "probability"],

            # English topics
            "poetry": ["poem", "verse", "stanza", "metaphor", "imagery", "rhyme"],
            "prose": ["novel", "short story", "narrative", "character", "plot"],
            "language": ["vocabulary", "grammar", "syntax", "punctuation"],
            "rhetoric": ["persuasion", "rhetoric", "argument", "evidence"],

            # Science topics
            "forces": ["newton", "acceleration", "velocity", "momentum", "friction"],
            "energy": ["kinetic", "potential", "heat", "temperature", "thermodynamic"],
            "waves": ["frequency", "wavelength", "amplitude", "sound", "light"],
            "atoms": ["electron", "nucleus", "atom", "molecule", "atomic"],
            "reactions": ["chemical", "reaction", "oxidation", "bonding", "catalyst"],
        }

        for question in questions:
            question_text = question.get("question", "").lower()

            for topic, keywords in keyword_mapping.items():
                if any(kw in question_text for kw in keywords):
                    if topic not in topics:
                        topics.append(topic)

        return topics if topics else ["general"]

    @staticmethod
    def get_topic_performance(
        db: DBSession,
        user_id: int,
        subject: str,
        days_back: int = 90
    ) -> Dict[str, Dict[str, Any]]:
        """
        Analyze performance by topic over specified period.

        Returns:
            {
                "topic_name": {
                    "attempts": N,
                    "accuracy": X%,
                    "average_score": Y,
                    "last_attempted": datetime,
                    "needs_review": bool,
                    "proficiency": "weak" | "developing" | "proficient" | "expert"
                }
            }
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)

        # Get recent quiz attempts for this subject
        attempts = db.query(QuizAttempt).filter(
            QuizAttempt.user_id == user_id,
            QuizAttempt.subject == subject,
            QuizAttempt.status == "completed",
            QuizAttempt.completed_at >= cutoff_date
        ).all()

        topic_performance = {}

        for attempt in attempts:
            # Get answers for this attempt
            answers = db.query(StudentAnswer).filter(
                StudentAnswer.quiz_attempt_id == attempt.id
            ).all()

            # For now, aggregate all answers as "general" topic
            # In production, would parse questions to extract specific topics
            if answers:
                if "general" not in topic_performance:
                    topic_performance["general"] = {
                        "attempts": 0,
                        "correct_count": 0,
                        "total_score": 0.0,
                        "last_attempted": None,
                    }

                topic_perf = topic_performance["general"]
                topic_perf["attempts"] += 1
                topic_perf["correct_count"] += sum(1 for a in answers if a.is_correct)
                topic_perf["total_score"] += attempt.score_percentage
                topic_perf["last_attempted"] = attempt.completed_at

        # Calculate statistics for each topic
        result = {}
        for topic, perf in topic_performance.items():
            attempts = perf["attempts"]
            accuracy = (perf["correct_count"] / (attempts * 5) * 100) if attempts > 0 else 0  # Assuming ~5 questions per attempt
            average_score = perf["total_score"] / attempts if attempts > 0 else 0

            # Determine proficiency level
            if accuracy >= 85:
                proficiency = "expert"
            elif accuracy >= 70:
                proficiency = "proficient"
            elif accuracy >= 50:
                proficiency = "developing"
            else:
                proficiency = "weak"

            result[topic] = {
                "attempts": attempts,
                "accuracy": round(accuracy, 1),
                "average_score": round(average_score, 1),
                "last_attempted": perf["last_attempted"],
                "needs_review": accuracy < 70,
                "proficiency": proficiency,
            }

        return result


class SpacedRepetitionService:
    """Implements spaced repetition algorithm for optimal review timing."""

    # Spaced repetition intervals (in days)
    INTERVALS = {
        0: 1,      # First review: 1 day
        1: 3,      # Second review: 3 days
        2: 7,      # Third review: 7 days
        3: 14,     # Fourth review: 14 days
        4: 30,     # Fifth review: 30 days
    }

    @staticmethod
    def calculate_next_review_date(
        last_attempted: datetime,
        accuracy: float,
        review_count: int = 0
    ) -> datetime:
        """
        Calculate optimal next review date using spaced repetition.

        Args:
            last_attempted: When topic was last reviewed
            accuracy: Accuracy percentage (0-100)
            review_count: How many times this topic has been reviewed

        Returns:
            Recommended datetime for next review
        """
        # Adjust interval based on accuracy
        base_interval = SpacedRepetitionService.INTERVALS.get(review_count, 60)

        if accuracy >= 85:
            # Doing well - extend interval
            interval_days = base_interval
        elif accuracy >= 70:
            # Okay - normal interval
            interval_days = base_interval // 2
        elif accuracy >= 50:
            # Struggling - shorter interval
            interval_days = base_interval // 4
        else:
            # Very weak - review soon
            interval_days = 1

        next_review = last_attempted + timedelta(days=interval_days)
        return next_review

    @staticmethod
    def get_topics_due_for_review(
        db: DBSession,
        user_id: int,
        subject: str
    ) -> List[Dict[str, Any]]:
        """
        Get list of topics that are due for review today.

        Returns topics sorted by:
        1. Weak areas first (accuracy < 70%)
        2. Days overdue (oldest first)
        3. Frequency of incorrect answers
        """
        topic_perf = TopicPerformanceService.get_topic_performance(db, user_id, subject)

        topics_due = []
        now = datetime.utcnow()

        for topic, perf in topic_perf.items():
            last_attempted = perf["last_attempted"]

            if last_attempted is None:
                # Never attempted - high priority
                days_since = float('inf')
            else:
                days_since = (now - last_attempted).days

            # Calculate priority score (lower = more urgent)
            weakness_factor = 100 - perf["accuracy"]  # Weak topics get higher score
            days_overdue = max(0, days_since - 7)  # After 7 days, consider overdue

            priority = (weakness_factor * 0.7) + (days_overdue * 0.3)

            if perf["needs_review"] or days_since > 7:
                topics_due.append({
                    "topic": topic,
                    "accuracy": perf["accuracy"],
                    "last_attempted": last_attempted,
                    "days_since": days_since,
                    "priority_score": priority,
                    "proficiency": perf["proficiency"],
                })

        # Sort by priority (highest first = most urgent)
        topics_due.sort(key=lambda x: x["priority_score"], reverse=True)

        return topics_due

    @staticmethod
    def get_study_schedule(
        db: DBSession,
        user_id: int,
        subject: str,
        days_ahead: int = 7
    ) -> List[Dict[str, Any]]:
        """
        Generate a study schedule for the next N days.

        Returns:
            List of recommended study sessions with timing and topics
        """
        topic_perf = TopicPerformanceService.get_topic_performance(db, user_id, subject)
        schedule = []
        now = datetime.utcnow()

        for day_offset in range(days_ahead):
            day_date = now + timedelta(days=day_offset)
            day_topics = []

            for topic, perf in topic_perf.items():
                next_review = SpacedRepetitionService.calculate_next_review_date(
                    perf["last_attempted"] or now,
                    perf["accuracy"],
                    0
                )

                if next_review.date() == day_date.date():
                    day_topics.append({
                        "topic": topic,
                        "urgency": "high" if perf["accuracy"] < 70 else "medium",
                        "reason": f"Weak area ({perf['accuracy']:.0f}% accuracy)" if perf["accuracy"] < 70 else "Regular review"
                    })

            if day_topics:
                schedule.append({
                    "date": day_date.date(),
                    "topics": day_topics,
                    "study_time_minutes": len(day_topics) * 15,  # 15 min per topic
                })

        return schedule
