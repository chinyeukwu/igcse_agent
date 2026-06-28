"""
Pearson Exam Papers Extractor
Extracts questions and marking schemes from Edexcel/Pearson PDFs.
"""

import pdfplumber
import re
from pathlib import Path
from typing import Optional, Dict, List
import logging

logger = logging.getLogger(__name__)


class PaperMetadata:
    """Metadata for a Pearson exam paper."""

    SUBJECT_CODES = {
        "4ma1": "Maths",
        "4ea1": "English Language",
        "4et1": "English Literature",
        "4sd0": "Science",
        "4fr1": "French",
        "4ch1": "Chemistry",
        "4bi1": "Biology",
        "4ph1": "Physics",
    }

    @staticmethod
    def extract_from_filename(filename: str) -> Dict:
        """Extract metadata from Pearson filename pattern."""
        metadata = {
            "filename": filename,
            "paper_code": None,
            "paper_number": None,
            "subject": None,
            "is_marking_scheme": False,
            "date": None,
        }

        # Check if it's a marking scheme
        if any(x in filename.lower() for x in ["marking scheme", "mark-scheme", "rms"]):
            metadata["is_marking_scheme"] = True

        # Extract paper code (e.g., 4ma1, 4ea1, etc.)
        code_match = re.search(r'(4[a-z]{2}\d)', filename)
        if code_match:
            code = code_match.group(1)
            metadata["paper_code"] = code
            metadata["subject"] = PaperMetadata.SUBJECT_CODES.get(code, "Unknown")

        # Extract paper number
        paper_match = re.search(r'paper[- ]?(\d)', filename, re.IGNORECASE)
        if paper_match:
            metadata["paper_number"] = int(paper_match.group(1))

        # Extract date
        date_match = re.search(r'(\d{8})', filename)
        if date_match:
            metadata["date"] = date_match.group(1)

        return metadata


class PaperExtractor:
    """Extracts content from Pearson exam papers and marking schemes."""

    def __init__(self, papers_dir: str = r"C:\Users\chiny\Downloads\pearson papers"):
        self.papers_dir = Path(papers_dir)
        self.papers = []
        self.marking_schemes = []

    def extract_all(self) -> Dict:
        """Extract all papers and marking schemes from the directory."""
        if not self.papers_dir.exists():
            logger.error(f"Papers directory not found: {self.papers_dir}")
            return {"papers": [], "marking_schemes": [], "errors": []}

        results = {"papers": [], "marking_schemes": [], "errors": []}

        for pdf_file in self.papers_dir.glob("*.pdf"):
            try:
                metadata = PaperMetadata.extract_from_filename(pdf_file.name)
                content = self._extract_pdf_text(pdf_file)

                paper_data = {
                    "filename": pdf_file.name,
                    "path": str(pdf_file),
                    "metadata": metadata,
                    "content": content,
                    "pages": len(content.split("\n")) // 50,  # Rough estimate
                }

                if metadata["is_marking_scheme"]:
                    results["marking_schemes"].append(paper_data)
                else:
                    results["papers"].append(paper_data)

                logger.info(f"Extracted: {pdf_file.name}")
            except Exception as e:
                error_msg = f"Error extracting {pdf_file.name}: {str(e)}"
                logger.error(error_msg)
                results["errors"].append(error_msg)

        return results

    def _extract_pdf_text(self, pdf_path: Path) -> str:
        """Extract text from a PDF file."""
        text_content = []
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        text_content.append(text)
        except Exception as e:
            logger.error(f"Failed to extract text from {pdf_path}: {e}")
            raise

        return "\n".join(text_content)

    def get_papers_by_subject(self) -> Dict[str, List]:
        """Organize papers by subject."""
        by_subject = {}
        for paper in self.papers:
            subject = paper["metadata"].get("subject", "Unknown")
            if subject not in by_subject:
                by_subject[subject] = []
            by_subject[subject].append(paper)

        return by_subject

    def get_marking_schemes_by_subject(self) -> Dict[str, List]:
        """Organize marking schemes by subject."""
        by_subject = {}
        for scheme in self.marking_schemes:
            subject = scheme["metadata"].get("subject", "Unknown")
            if subject not in by_subject:
                by_subject[subject] = []
            by_subject[subject].append(scheme)

        return by_subject


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    extractor = PaperExtractor()
    results = extractor.extract_all()

    print(f"\n✓ Extracted {len(results['papers'])} exam papers")
    print(f"✓ Extracted {len(results['marking_schemes'])} marking schemes")

    if results["errors"]:
        print(f"\n✗ Errors encountered ({len(results['errors'])}):")
        for error in results["errors"]:
            print(f"  - {error}")

    # Display summary by subject
    papers_by_subject = {}
    for paper in results["papers"]:
        subject = paper["metadata"].get("subject", "Unknown")
        if subject not in papers_by_subject:
            papers_by_subject[subject] = 0
        papers_by_subject[subject] += 1

    print("\nPapers by Subject:")
    for subject, count in sorted(papers_by_subject.items()):
        print(f"  {subject}: {count}")
