"""Papers module for managing Pearson exam papers and marking schemes."""

from src.papers.extractor import PaperExtractor, PaperMetadata
from src.papers.reference_manager import PaperReferenceManager
from src.papers.question_extractor import PearsonQuestionExtractor

__all__ = [
    "PaperExtractor",
    "PaperMetadata",
    "PaperReferenceManager",
    "PearsonQuestionExtractor",
]
