"""
Quiz Service for managing quiz attempts, scoring, and difficulty calibration.
"""

import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session as DBSession

from src.database.models import (
    QuizAttempt, StudentAnswer, PaperQuestion,
    StudentDifficultyProfile, User
)

logger = logging.getLogger(__name__)


class QuizScoringService:
    """Handles quiz scoring and answer evaluation."""

    @staticmethod
    def parse_marking_scheme(marking_scheme: str) -> Dict[str, Any]:
        """Parse marking scheme text into structured format."""
        # Simple parsing - can be enhanced for complex schemes
        lines = marking_scheme.split('\n') if marking_scheme else []
        return {
            "raw_text": marking_scheme,
            "line_count": len(lines),
            "lines": lines
        }

    @staticmethod
    def score_multiple_choice(student_answer: str, correct_answer: str, marks_total: float = 1.0) -> Tuple[bool, float, str]:
        """Score multiple choice answer."""
        is_correct = student_answer.strip().lower() == correct_answer.strip().lower()
        score = marks_total if is_correct else 0.0
        feedback = "Correct!" if is_correct else f"Incorrect. Correct answer: {correct_answer}"
        return is_correct, score, feedback

    @staticmethod
    def score_short_answer(student_answer: str, correct_answer: str, marking_scheme: str, marks_total: float = 1.0) -> Tuple[bool, float, str]:
        """Score short answer based on marking scheme criteria."""
        # This could be enhanced with fuzzy matching or AI-based evaluation
        keywords = correct_answer.lower().split()
        student_words = student_answer.lower().split()

        # Calculate partial credit based on keyword matching
        matched_keywords = sum(1 for kw in keywords if any(kw in sw for sw in student_words))
        accuracy_ratio = matched_keywords / len(keywords) if keywords else 0.0

        score = marks_total * accuracy_ratio
        is_correct = accuracy_ratio >= 0.8

        feedback = f"Partial credit: {matched_keywords}/{len(keywords)} key concepts identified.\n"
        if marking_scheme:
            feedback += f"Marking scheme: {marking_scheme[:200]}..."

        return is_correct, score, feedback

    @staticmethod
    def evaluate_answer(
        student_answer: str,
        paper_question: PaperQuestion,
        marks_total: float = 1.0
    ) -> Tuple[bool, float, str]:
        """Evaluate student answer against question and marking scheme."""

        if paper_question.question_type == "multiple_choice":
            return QuizScoringService.score_multiple_choice(
                student_answer,
                paper_question.correct_answer or "",
                marks_total
            )
        else:
            return QuizScoringService.score_short_answer(
                student_answer,
                paper_question.correct_answer or "",
                paper_question.marking_scheme or "",
                marks_total
            )


class DifficultyCalibrationService:
    """Handles adaptive difficulty calibration based on student performance."""

    CALIBRATION_RULES = {
        "increase": {
            "accuracy_threshold": 80.0,  # Must score 80%+
            "consecutive_correct": 2,    # Must succeed 2 quizzes in a row
        },
        "decrease": {
            "accuracy_threshold": 50.0,  # Below 50% accuracy
            "check_after_quizzes": 3,    # After 3 quizzes
        },
        "hold": {
            "min_quizzes": 1,
            "accuracy_range": (50.0, 80.0),  # 50-80% = stay at current level
        }
    }

    @staticmethod
    def get_or_create_profile(db: DBSession, user_id: int, subject: str) -> StudentDifficultyProfile:
        """Get or create difficulty profile for student."""
        profile = db.query(StudentDifficultyProfile).filter(
            StudentDifficultyProfile.user_id == user_id,
            StudentDifficultyProfile.subject == subject
        ).first()

        if not profile:
            profile = StudentDifficultyProfile(
                user_id=user_id,
                subject=subject,
                current_difficulty="easy"
            )
            db.add(profile)
            db.commit()

        return profile

    @staticmethod
    def update_profile_after_quiz(
        db: DBSession,
        user_id: int,
        subject: str,
        quiz_score_percentage: float
    ) -> str:
        """Update profile after quiz completion and return new difficulty."""
        profile = DifficultyCalibrationService.get_or_create_profile(db, user_id, subject)

        # Update statistics
        profile.quizzes_completed += 1
        profile.last_quiz_score = quiz_score_percentage

        # Update moving average
        if profile.average_score is None:
            profile.average_score = quiz_score_percentage
        else:
            profile.average_score = (profile.average_score * 0.7 + quiz_score_percentage * 0.3)

        # Update consecutive correct
        if quiz_score_percentage >= DifficultyCalibrationService.CALIBRATION_RULES["increase"]["accuracy_threshold"]:
            profile.consecutive_correct += 1
        else:
            profile.consecutive_correct = 0

        # Calculate accuracy rate (moving average)
        profile.accuracy_rate = profile.average_score or quiz_score_percentage

        # Apply calibration rules
        old_difficulty = profile.current_difficulty
        new_difficulty = DifficultyCalibrationService.calibrate_difficulty(profile)

        if new_difficulty != old_difficulty:
            logger.info(f"User {user_id} {subject}: {old_difficulty} → {new_difficulty} (score: {quiz_score_percentage:.1f}%)")
            profile.current_difficulty = new_difficulty

        profile.last_updated = datetime.utcnow()
        db.commit()

        return profile.current_difficulty

    @staticmethod
    def calibrate_difficulty(profile: StudentDifficultyProfile) -> str:
        """Determine if difficulty should change based on profile stats."""
        rules = DifficultyCalibrationService.CALIBRATION_RULES

        # Check if should increase
        if (profile.accuracy_rate >= rules["increase"]["accuracy_threshold"] and
                profile.consecutive_correct >= rules["increase"]["consecutive_correct"] and
                profile.current_difficulty != "hard"):
            return "hard" if profile.current_difficulty == "medium" else "medium"

        # Check if should decrease
        if (profile.accuracy_rate < rules["decrease"]["accuracy_threshold"] and
                profile.quizzes_completed >= rules["decrease"]["check_after_quizzes"] and
                profile.current_difficulty != "easy"):
            return "easy" if profile.current_difficulty == "medium" else "medium"

        # Otherwise, stay at current level
        return profile.current_difficulty


class QuizAttemptService:
    """Handles quiz attempt tracking and retrieval."""

    @staticmethod
    def create_quiz_attempt(
        db: DBSession,
        user_id: int,
        subject: str,
        difficulty_level: str,
        question_count: int
    ) -> QuizAttempt:
        """Create a new quiz attempt record."""
        attempt = QuizAttempt(
            user_id=user_id,
            subject=subject,
            difficulty_level=difficulty_level,
            question_count=question_count,
            score_percentage=0.0,
            status="in_progress"
        )
        db.add(attempt)
        db.commit()
        logger.info(f"Created quiz attempt {attempt.id} for user {user_id}")
        return attempt

    @staticmethod
    def record_answer(
        db: DBSession,
        quiz_attempt_id: int,
        question_id: Optional[int],
        question_text: str,
        student_answer: str,
        correct_answer: str,
        is_correct: bool,
        score_earned: float,
        marks_total: float,
        feedback: str
    ) -> StudentAnswer:
        """Record a student's answer to a question."""
        answer = StudentAnswer(
            quiz_attempt_id=quiz_attempt_id,
            question_id=question_id,
            question_text=question_text,
            student_answer=student_answer,
            correct_answer=correct_answer,
            is_correct=is_correct,
            score_earned=score_earned,
            marks_total=marks_total,
            feedback=feedback
        )
        db.add(answer)
        db.commit()
        return answer

    @staticmethod
    def complete_quiz_attempt(
        db: DBSession,
        attempt_id: int,
        time_taken_seconds: Optional[int] = None
    ) -> QuizAttempt:
        """Complete a quiz attempt and calculate final score."""
        attempt = db.query(QuizAttempt).filter(QuizAttempt.id == attempt_id).first()

        if not attempt:
            raise ValueError(f"Quiz attempt {attempt_id} not found")

        # Calculate score
        answers = db.query(StudentAnswer).filter(StudentAnswer.quiz_attempt_id == attempt_id).all()

        if answers:
            total_earned = sum(a.score_earned for a in answers)
            total_marks = sum(a.marks_total for a in answers)
            attempt.score_percentage = (total_earned / total_marks * 100) if total_marks > 0 else 0.0
        else:
            attempt.score_percentage = 0.0

        attempt.completed_at = datetime.utcnow()
        attempt.status = "completed"
        if time_taken_seconds:
            attempt.time_taken_seconds = time_taken_seconds

        db.commit()

        # Update difficulty profile
        DifficultyCalibrationService.update_profile_after_quiz(
            db,
            attempt.user_id,
            attempt.subject,
            attempt.score_percentage
        )

        logger.info(f"Completed quiz attempt {attempt_id} with score {attempt.score_percentage:.1f}%")
        return attempt

    @staticmethod
    def get_user_quiz_history(
        db: DBSession,
        user_id: int,
        subject: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Retrieve quiz history for a user."""
        query = db.query(QuizAttempt).filter(
            QuizAttempt.user_id == user_id,
            QuizAttempt.status == "completed"
        )

        if subject:
            query = query.filter(QuizAttempt.subject == subject)

        attempts = query.order_by(QuizAttempt.completed_at.desc()).limit(limit).all()

        return [
            {
                "id": a.id,
                "subject": a.subject,
                "difficulty": a.difficulty_level,
                "score": a.score_percentage,
                "questions": a.question_count,
                "time_taken": a.time_taken_seconds,
                "completed_at": a.completed_at.isoformat() if a.completed_at else None,
            }
            for a in attempts
        ]

    @staticmethod
    def get_user_performance_summary(
        db: DBSession,
        user_id: int
    ) -> Dict[str, Any]:
        """Get performance summary across all subjects."""
        attempts = db.query(QuizAttempt).filter(
            QuizAttempt.user_id == user_id,
            QuizAttempt.status == "completed"
        ).all()

        if not attempts:
            return {"total_quizzes": 0, "subjects": {}}

        # Group by subject
        by_subject = {}
        for attempt in attempts:
            if attempt.subject not in by_subject:
                by_subject[attempt.subject] = []
            by_subject[attempt.subject].append(attempt)

        # Calculate stats per subject
        subject_stats = {}
        for subject, subject_attempts in by_subject.items():
            scores = [a.score_percentage for a in subject_attempts]
            subject_stats[subject] = {
                "quizzes_completed": len(subject_attempts),
                "average_score": sum(scores) / len(scores),
                "best_score": max(scores),
                "worst_score": min(scores),
                "improvement": scores[-1] - scores[0] if len(scores) > 1 else 0,
            }

        return {
            "total_quizzes": len(attempts),
            "subjects": subject_stats,
        }
