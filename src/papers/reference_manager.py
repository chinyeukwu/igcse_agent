"""
Pearson Papers Reference Manager
Manages Edexcel/Pearson exam papers as references for quiz generation.
Stores paper paths and metadata indexed by subject, paper code, and difficulty.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class PaperReference:
    """Reference to a Pearson exam paper or marking scheme."""

    def __init__(
        self,
        filename: str,
        filepath: str,
        subject: str,
        paper_code: str,
        paper_number: int,
        is_marking_scheme: bool = False,
        date: Optional[str] = None,
    ):
        self.filename = filename
        self.filepath = filepath
        self.subject = subject
        self.paper_code = paper_code
        self.paper_number = paper_number
        self.is_marking_scheme = is_marking_scheme
        self.date = date

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "filename": self.filename,
            "filepath": self.filepath,
            "subject": self.subject,
            "paper_code": self.paper_code,
            "paper_number": self.paper_number,
            "is_marking_scheme": self.is_marking_scheme,
            "date": self.date,
        }

    @staticmethod
    def extract_from_filename(filename: str) -> Dict:
        """Extract metadata from filename format."""
        import re
        # Expected format: 4ma1_r_ms12_20101h_final.pdf or similar
        match = re.search(r'(\d[a-z]{2,3}\d)_.*?_?(\d+)?', filename.lower())
        if match:
            paper_code = match.group(1)
            paper_number = int(match.group(2)) if match.group(2) else 1
            return {
                "paper_code": paper_code,
                "paper_number": paper_number,
                "is_marking_scheme": "ms" in filename.lower() or "scheme" in filename.lower(),
            }
        return {"paper_code": "unknown", "paper_number": 1, "is_marking_scheme": False}


class PaperReferenceManager:
    """Manages references to Pearson exam papers."""

    SUBJECT_CODES = {
        "4ma1": "Maths",
        "4ea1": "English Language",
        "4et1": "English Literature",
        "4sd0": "Science",
        "4bi0": "Biology",
        "4ch0": "Chemistry",
        "4ph0": "Physics",
        "4fr1": "French",
    }

    def __init__(
        self,
        papers_dir: str = r"C:\Users\chiny\Downloads\pearson papers",
        cache_file: Optional[str] = None,
    ):
        self.papers_dir = Path(papers_dir)
        self.cache_file = Path(cache_file) if cache_file else None
        self.papers: Dict[str, List[PaperReference]] = {}
        self.marking_schemes: Dict[str, List[PaperReference]] = {}

    def scan_directory(self) -> Dict:
        """Scan the papers directory and organize all PDFs by subject."""
        if not self.papers_dir.exists():
            logger.error(f"Papers directory not found: {self.papers_dir}")
            return {"papers": 0, "marking_schemes": 0, "subjects": []}

        self.papers = {}
        self.marking_schemes = {}

        for pdf_file in sorted(self.papers_dir.glob("*.pdf")):
            try:
                metadata = self._parse_filename(pdf_file.name)
                subject = metadata["subject"]

                paper_ref = PaperReference(
                    filename=pdf_file.name,
                    filepath=str(pdf_file),
                    subject=subject,
                    paper_code=metadata["paper_code"],
                    paper_number=metadata["paper_number"],
                    is_marking_scheme=metadata["is_marking_scheme"],
                    date=metadata["date"],
                )

                if metadata["is_marking_scheme"]:
                    if subject not in self.marking_schemes:
                        self.marking_schemes[subject] = []
                    self.marking_schemes[subject].append(paper_ref)
                else:
                    if subject not in self.papers:
                        self.papers[subject] = []
                    self.papers[subject].append(paper_ref)

                logger.info(f"Indexed: {pdf_file.name}")

            except Exception as e:
                logger.error(f"Error indexing {pdf_file.name}: {e}")

        return self.get_summary()

    def _parse_filename(self, filename: str) -> Dict:
        """Parse Pearson filename to extract metadata."""
        import re

        metadata = {
            "filename": filename,
            "paper_code": "UNKNOWN",
            "paper_number": 0,
            "subject": "Unknown",
            "is_marking_scheme": False,
            "date": None,
        }

        # Check if it's a marking scheme
        if any(x in filename.lower() for x in ["marking", "mark-scheme", "rms", "ms"]):
            metadata["is_marking_scheme"] = True

        # Extract paper code (e.g., 4ma1, 4ea1)
        code_match = re.search(r"(4[a-z]{2}\d)", filename, re.IGNORECASE)
        if code_match:
            code = code_match.group(1).lower()
            metadata["paper_code"] = code
            metadata["subject"] = self.SUBJECT_CODES.get(code, "Unknown")

        # Extract paper number
        paper_match = re.search(r"paper[- ]?(\d)", filename, re.IGNORECASE)
        if paper_match:
            metadata["paper_number"] = int(paper_match.group(1))

        # Extract date
        date_match = re.search(r"(\d{8})", filename)
        if date_match:
            metadata["date"] = date_match.group(1)

        return metadata

    def get_summary(self) -> Dict:
        """Get summary of indexed papers."""
        total_papers = sum(len(papers) for papers in self.papers.values())
        total_schemes = sum(len(schemes) for schemes in self.marking_schemes.values())

        return {
            "papers": total_papers,
            "marking_schemes": total_schemes,
            "subjects": sorted(
                set(list(self.papers.keys()) + list(self.marking_schemes.keys()))
            ),
        }

    def get_papers_for_subject(self, subject: str) -> List[Dict]:
        """Get all exam papers for a specific subject."""
        papers = self.papers.get(subject, [])
        return [p.to_dict() for p in papers]

    def get_marking_schemes_for_subject(self, subject: str) -> List[Dict]:
        """Get all marking schemes for a specific subject."""
        schemes = self.marking_schemes.get(subject, [])
        return [s.to_dict() for s in schemes]

    def get_all_papers_by_subject(self) -> Dict[str, List[Dict]]:
        """Get all papers organized by subject."""
        return {
            subject: [p.to_dict() for p in papers]
            for subject, papers in self.papers.items()
        }

    def get_all_marking_schemes_by_subject(self) -> Dict[str, List[Dict]]:
        """Get all marking schemes organized by subject."""
        return {
            subject: [s.to_dict() for s in schemes]
            for subject, schemes in self.marking_schemes.items()
        }

    def get_context_for_quiz_generation(self, subject: str) -> str:
        """Generate context string for quiz generation prompt."""
        papers = self.get_papers_for_subject(subject)
        schemes = self.get_marking_schemes_for_subject(subject)

        context = f"\n## Pearson Exam Papers for {subject}\n\n"

        if papers:
            context += f"**Available Exam Papers ({len(papers)}):**\n"
            for paper in papers:
                context += f"- {paper['filename']}\n"

        if schemes:
            context += f"\n**Available Marking Schemes ({len(schemes)}):**\n"
            for scheme in schemes:
                context += f"- {scheme['filename']}\n"

        if not papers and not schemes:
            context += f"(No papers or marking schemes available for {subject})"

        return context

    def save_index(self, filepath: str) -> None:
        """Save paper index to JSON file for caching."""
        index = {
            "papers": self.get_all_papers_by_subject(),
            "marking_schemes": self.get_all_marking_schemes_by_subject(),
            "summary": self.get_summary(),
        }

        Path(filepath).write_text(json.dumps(index, indent=2))
        logger.info(f"Saved paper index to {filepath}")

    def load_index(self, filepath: str) -> bool:
        """Load paper index from JSON file."""
        try:
            index = json.loads(Path(filepath).read_text())

            # Rebuild objects from dicts
            for subject, papers in index.get("papers", {}).items():
                self.papers[subject] = [
                    PaperReference(
                        filename=p["filename"],
                        filepath=p["filepath"],
                        subject=p["subject"],
                        paper_code=p["paper_code"],
                        paper_number=p["paper_number"],
                        is_marking_scheme=False,
                        date=p.get("date"),
                    )
                    for p in papers
                ]

            for subject, schemes in index.get("marking_schemes", {}).items():
                self.marking_schemes[subject] = [
                    PaperReference(
                        filename=s["filename"],
                        filepath=s["filepath"],
                        subject=s["subject"],
                        paper_code=s["paper_code"],
                        paper_number=s["paper_number"],
                        is_marking_scheme=True,
                        date=s.get("date"),
                    )
                    for s in schemes
                ]

            logger.info(f"Loaded paper index from {filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to load paper index: {e}")
            return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    manager = PaperReferenceManager()
    summary = manager.scan_directory()

    print(f"\nPearson Papers Index Summary:")
    print(f"  Total Exam Papers: {summary['papers']}")
    print(f"  Total Marking Schemes: {summary['marking_schemes']}")
    print(f"\n  Subjects Indexed: {', '.join(summary['subjects'])}")

    # Show details by subject
    print(f"\nDetails by Subject:")
    for subject in summary["subjects"]:
        papers = manager.get_papers_for_subject(subject)
        schemes = manager.get_marking_schemes_for_subject(subject)
        print(f"  {subject}: {len(papers)} papers, {len(schemes)} schemes")

    # Save index for future use
    index_file = "data/paper_index.json"
    manager.save_index(index_file)
