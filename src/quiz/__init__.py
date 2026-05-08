"""
Quiz module for generating and managing IGCSE quizzes.
Provides quiz generation, scoring, and 60-day history management.
"""

from src.quiz.quiz_generator import QuizGenerator
from src.quiz.quiz_service import QuizService

__all__ = ["QuizGenerator", "QuizService"]
