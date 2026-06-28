"""
Question Extractor for parsing Pearson papers and storing in database.
Extracts individual questions and marking schemes from PDF papers.
"""

import logging
import re
from pathlib import Path
from typing import List, Dict, Optional
from sqlalchemy.orm import Session as DBSession

from src.database.models import PaperQuestion
from src.papers.reference_manager import PaperMetadata

logger = logging.getLogger(__name__)


class PearsonQuestionExtractor:
    """Extracts questions from Pearson papers without complex PDF parsing."""

    # Subject difficulty inference rules
    DIFFICULTY_PATTERNS = {
        "easy": ["basic", "simple", "identify", "name", "state", "list", "define"],
        "medium": ["explain", "describe", "calculate", "compare", "analyse", "discuss"],
        "hard": ["evaluate", "deduce", "justify", "suggest", "predict", "critical", "synthesis"],
    }

    COMMAND_WORDS = {
        "identify": "easy",
        "name": "easy",
        "state": "easy",
        "define": "easy",
        "list": "easy",
        "describe": "medium",
        "explain": "medium",
        "calculate": "medium",
        "compare": "medium",
        "analyse": "hard",
        "evaluate": "hard",
        "discuss": "hard",
        "justify": "hard",
        "deduce": "hard",
    }

    @staticmethod
    def infer_difficulty(question_text: str) -> str:
        """Infer difficulty level from question text using command words."""
        question_lower = question_text.lower()

        # Check for command words
        for word, difficulty in PearsonQuestionExtractor.COMMAND_WORDS.items():
            if word in question_lower:
                return difficulty

        # Default to medium if no command word found
        return "medium"

    @staticmethod
    def extract_marking_scheme_from_question(question_text: str) -> Optional[str]:
        """Extract marking information if present in question text."""
        # Look for patterns like "[ /5]", "Marks: 5", etc.
        marks_pattern = r'\[\s*/?(\d+)\s*\]|Marks?:\s*(\d+)'
        match = re.search(marks_pattern, question_text)

        if match:
            marks = match.group(1) or match.group(2)
            return f"Total marks: {marks}"

        return None

    @staticmethod
    def parse_multiple_choice_options(text: str) -> Optional[List[str]]:
        """Parse multiple choice options from text."""
        # Common patterns: A) ..., B) ..., etc. or 1) ..., 2) ..., etc.
        options = []

        # Try letter pattern
        letter_pattern = r'^[A-D]\)\s+(.+)$'
        lines = [line.strip() for line in text.split('\n') if line.strip()]

        for line in lines:
            match = re.match(letter_pattern, line)
            if match:
                options.append(match.group(1).strip())

        if len(options) == 4:
            return options

        # Try number pattern
        options = []
        number_pattern = r'^[1-4]\)\s+(.+)$'
        for line in lines:
            match = re.match(number_pattern, line)
            if match:
                options.append(match.group(1).strip())

        return options if len(options) == 4 else None

    @staticmethod
    def create_placeholder_questions(
        db: DBSession,
        paper_code: str,
        paper_number: int,
        subject: str,
        source_filename: str
    ) -> List[PaperQuestion]:
        """Create placeholder questions from Pearson paper (for manual addition later)."""
        questions = []

        # Create 5 placeholder questions per paper
        for q_num in range(1, 6):
            difficulty = PearsonQuestionExtractor.infer_difficulty(f"Question {q_num}")

            question = PaperQuestion(
                paper_code=paper_code,
                paper_number=paper_number,
                subject=subject,
                question_number=q_num,
                question_text=f"[Placeholder] Question {q_num} from {paper_code} Paper {paper_number}",
                question_type="multiple_choice",
                options_json=None,
                correct_answer=None,
                marking_scheme=f"Refer to {source_filename} for marking scheme",
                marks_total=q_num * 5,  # Vary marks
                source_filename=source_filename,
                difficulty_level=difficulty,
            )
            questions.append(question)
            db.add(question)

        db.commit()
        logger.info(f"Created {len(questions)} placeholder questions for {paper_code} Paper {paper_number}")
        return questions

    @staticmethod
    def import_papers_to_database(
        db: DBSession,
        papers_dir: str = r"C:\Users\chiny\Downloads\pearson papers",
        create_placeholders: bool = True
    ) -> Dict[str, int]:
        """Import all papers from directory to database."""
        from src.papers.reference_manager import PaperReferenceManager

        manager = PaperReferenceManager(papers_dir)
        manager.scan_directory()

        stats = {
            "papers_processed": 0,
            "questions_created": 0,
            "errors": 0,
        }

        # Process exam papers
        for subject, papers in manager.get_all_papers_by_subject().items():
            for paper in papers:
                try:
                    metadata = PaperMetadata.extract_from_filename(paper["filename"])

                    if create_placeholders:
                        # Create placeholder questions that can be manually filled in later
                        questions = PearsonQuestionExtractor.create_placeholder_questions(
                            db,
                            paper_code=metadata["paper_code"],
                            paper_number=metadata["paper_number"] or 1,
                            subject=subject,
                            source_filename=paper["filename"]
                        )
                        stats["questions_created"] += len(questions)

                    stats["papers_processed"] += 1

                except Exception as e:
                    logger.error(f"Error processing {paper['filename']}: {e}")
                    stats["errors"] += 1

        logger.info(f"Import complete: {stats['papers_processed']} papers, {stats['questions_created']} questions")
        return stats

    @staticmethod
    def add_manual_question(
        db: DBSession,
        paper_code: str,
        paper_number: int,
        subject: str,
        question_number: int,
        question_text: str,
        question_type: str,
        correct_answer: str,
        marking_scheme: str,
        marks_total: int = 5,
        options_json: Optional[str] = None,
        source_filename: str = "manual_entry",
        difficulty_level: str = "medium"
    ) -> PaperQuestion:
        """Add a manually entered question to the database."""
        question = PaperQuestion(
            paper_code=paper_code,
            paper_number=paper_number,
            subject=subject,
            question_number=question_number,
            question_text=question_text,
            question_type=question_type,
            options_json=options_json,
            correct_answer=correct_answer,
            marking_scheme=marking_scheme,
            marks_total=marks_total,
            source_filename=source_filename,
            difficulty_level=difficulty_level or PearsonQuestionExtractor.infer_difficulty(question_text),
        )
        db.add(question)
        db.commit()
        logger.info(f"Added question {question_number} from {paper_code} Paper {paper_number}")
        return question
