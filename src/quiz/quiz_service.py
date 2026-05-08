"""
Quiz service for managing quiz attempts, scoring, and history.
Handles 60-day retention policy with automatic cleanup.
"""

import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session

from src.database.models import QuizHistory


class QuizService:
    """Service for managing quiz attempts and history."""

    RETENTION_DAYS = 60  # Keep quiz history for 60 days

    @staticmethod
    def calculate_score(
        questions: List[Dict[str, Any]],
        user_answers: List[int]
    ) -> Tuple[float, int]:
        """
        Calculate quiz score based on user answers.
        
        Args:
            questions: List of quiz questions with correct_answer field
            user_answers: List of user's selected answer indices
        
        Returns:
            Tuple of (score_percentage: float, correct_count: int)
        """
        if len(questions) == 0:
            return 0.0, 0
        
        if len(user_answers) != len(questions):
            return 0.0, 0
        
        correct_count = 0
        
        for i, question in enumerate(questions):
            if i < len(user_answers):
                # Get correct answer index
                correct_idx = question.get("correct_answer", -1)
                
                # Check if user's answer is correct
                if user_answers[i] == correct_idx:
                    correct_count += 1
        
        score_percentage = round((correct_count / len(questions)) * 100, 2)
        return score_percentage, correct_count

    @staticmethod
    def save_quiz_attempt(
        db_session: Session,
        user_id: int,
        subject: str,
        topic: str,
        difficulty: str,
        questions: List[Dict[str, Any]],
        user_answers: List[int],
        time_taken_seconds: Optional[int] = None,
        is_offline: bool = False,
        language_code: str = "en"
    ) -> Tuple[bool, Optional[int], str]:
        """
        Save a quiz attempt to history.
        
        Args:
            db_session: Database session
            user_id: User ID
            subject: IGCSE subject
            topic: Quiz topic/title
            difficulty: Difficulty level
            questions: Quiz questions
            user_answers: User's answers
            time_taken_seconds: Time spent on quiz
            is_offline: Whether quiz was taken offline
            language_code: Language code
        
        Returns:
            Tuple of (success, quiz_history_id, error_message)
        """
        try:
            # Calculate score
            score, correct_count = QuizService.calculate_score(questions, user_answers)
            
            # Serialize questions and answers
            questions_json = json.dumps(questions, ensure_ascii=False)
            user_answers_json = json.dumps(user_answers)
            
            # Create quiz history record
            quiz_record = QuizHistory(
                user_id=user_id,
                subject=subject,
                topic=topic,
                difficulty=difficulty,
                language_code=language_code,
                questions_json=questions_json,
                user_answers_json=user_answers_json,
                score=score,
                time_taken_seconds=time_taken_seconds,
                created_at=datetime.utcnow(),
                is_offline=is_offline,
                synced_at=None if is_offline else datetime.utcnow()
            )
            
            db_session.add(quiz_record)
            db_session.commit()
            
            return True, quiz_record.id, ""
        
        except Exception as e:
            db_session.rollback()
            return False, None, f"Error saving quiz: {str(e)}"

    @staticmethod
    def get_quiz_history(
        db_session: Session,
        user_id: int,
        subject: Optional[str] = None,
        limit: int = 50,
        within_retention: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get quiz history for a user with optional filtering.
        
        Args:
            db_session: Database session
            user_id: User ID
            subject: Filter by subject (optional)
            limit: Maximum records to return
            within_retention: Only include recent (within 60 days)
        
        Returns:
            List of quiz history records
        """
        try:
            query = db_session.query(QuizHistory).filter(
                QuizHistory.user_id == user_id
            )
            
            # Filter by retention period if requested
            if within_retention:
                retention_date = datetime.utcnow() - timedelta(days=QuizService.RETENTION_DAYS)
                query = query.filter(QuizHistory.created_at > retention_date)
            
            # Filter by subject if provided
            if subject:
                query = query.filter(QuizHistory.subject == subject.lower())
            
            # Order by most recent first
            records = query.order_by(QuizHistory.created_at.desc()).limit(limit).all()
            
            return [
                {
                    "id": r.id,
                    "subject": r.subject,
                    "topic": r.topic,
                    "difficulty": r.difficulty,
                    "score": r.score,
                    "correct_count": len(json.loads(r.user_answers_json)) 
                                     if r.user_answers_json else 0,
                    "total_questions": len(json.loads(r.questions_json)) 
                                       if r.questions_json else 0,
                    "time_taken_seconds": r.time_taken_seconds,
                    "is_offline": r.is_offline,
                    "created_at": r.created_at.isoformat(),
                    "synced_at": r.synced_at.isoformat() if r.synced_at else None
                }
                for r in records
            ]
        
        except Exception as e:
            print(f"Error fetching quiz history: {str(e)}")
            return []

    @staticmethod
    def get_quiz_statistics(
        db_session: Session,
        user_id: int,
        within_retention: bool = True
    ) -> Dict[str, Any]:
        """
        Get quiz performance statistics for a user.
        
        Args:
            db_session: Database session
            user_id: User ID
            within_retention: Only analyze recent quizzes
        
        Returns:
            Statistics dictionary with metrics
        """
        try:
            query = db_session.query(QuizHistory).filter(
                QuizHistory.user_id == user_id
            )
            
            if within_retention:
                retention_date = datetime.utcnow() - timedelta(days=QuizService.RETENTION_DAYS)
                query = query.filter(QuizHistory.created_at > retention_date)
            
            records = query.all()
            
            if not records:
                return {
                    "total_quizzes": 0,
                    "average_score": 0.0,
                    "highest_score": 0.0,
                    "lowest_score": 0.0,
                    "by_subject": {},
                    "by_difficulty": {}
                }
            
            total_quizzes = len(records)
            scores = [r.score for r in records]
            average_score = round(sum(scores) / len(scores), 2) if scores else 0
            
            # Statistics by subject
            by_subject = {}
            by_difficulty = {}
            
            for record in records:
                # By subject
                if record.subject not in by_subject:
                    by_subject[record.subject] = {"count": 0, "avg_score": 0, "scores": []}
                by_subject[record.subject]["count"] += 1
                by_subject[record.subject]["scores"].append(record.score)
                
                # By difficulty
                if record.difficulty not in by_difficulty:
                    by_difficulty[record.difficulty] = {"count": 0, "avg_score": 0, "scores": []}
                by_difficulty[record.difficulty]["count"] += 1
                by_difficulty[record.difficulty]["scores"].append(record.score)
            
            # Calculate averages
            for subj in by_subject:
                scores_list = by_subject[subj]["scores"]
                by_subject[subj]["avg_score"] = round(sum(scores_list) / len(scores_list), 2)
                del by_subject[subj]["scores"]
            
            for diff in by_difficulty:
                scores_list = by_difficulty[diff]["scores"]
                by_difficulty[diff]["avg_score"] = round(sum(scores_list) / len(scores_list), 2)
                del by_difficulty[diff]["scores"]
            
            return {
                "total_quizzes": total_quizzes,
                "average_score": average_score,
                "highest_score": max(scores),
                "lowest_score": min(scores),
                "by_subject": by_subject,
                "by_difficulty": by_difficulty
            }
        
        except Exception as e:
            print(f"Error calculating statistics: {str(e)}")
            return {"error": str(e)}

    @staticmethod
    def cleanup_old_quizzes(db_session: Session) -> int:
        """
        Delete quiz history older than retention period.
        Should be run periodically (e.g., daily).
        
        Args:
            db_session: Database session
        
        Returns:
            Number of records deleted
        """
        try:
            retention_date = datetime.utcnow() - timedelta(days=QuizService.RETENTION_DAYS)
            
            old_records = db_session.query(QuizHistory).filter(
                QuizHistory.created_at < retention_date
            ).all()
            
            count = len(old_records)
            
            for record in old_records:
                db_session.delete(record)
            
            db_session.commit()
            return count
        
        except Exception as e:
            db_session.rollback()
            print(f"Error cleaning up old quizzes: {str(e)}")
            return 0

    @staticmethod
    def get_quiz_detail(
        db_session: Session,
        user_id: int,
        quiz_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get detailed view of a specific quiz attempt.
        
        Args:
            db_session: Database session
            user_id: User ID
            quiz_id: Quiz history ID
        
        Returns:
            Detailed quiz information or None
        """
        try:
            quiz = db_session.query(QuizHistory).filter(
                QuizHistory.id == quiz_id,
                QuizHistory.user_id == user_id
            ).first()
            
            if not quiz:
                return None
            
            # Parse questions and answers
            questions = json.loads(quiz.questions_json) if quiz.questions_json else []
            user_answers = json.loads(quiz.user_answers_json) if quiz.user_answers_json else []
            
            # Create detailed response
            detail = {
                "id": quiz.id,
                "subject": quiz.subject,
                "topic": quiz.topic,
                "difficulty": quiz.difficulty,
                "score": quiz.score,
                "time_taken_seconds": quiz.time_taken_seconds,
                "created_at": quiz.created_at.isoformat(),
                "questions": []
            }
            
            # Add question details with user answers
            for i, question in enumerate(questions):
                q_detail = {
                    "number": i + 1,
                    "question": question.get("question", ""),
                    "options": question.get("options", []),
                    "correct_answer_index": question.get("correct_answer", -1),
                    "explanation": question.get("explanation", ""),
                    "user_answer_index": user_answers[i] if i < len(user_answers) else -1,
                    "is_correct": user_answers[i] == question.get("correct_answer", -1) if i < len(user_answers) else False
                }
                detail["questions"].append(q_detail)
            
            return detail
        
        except Exception as e:
            print(f"Error fetching quiz detail: {str(e)}")
            return None
