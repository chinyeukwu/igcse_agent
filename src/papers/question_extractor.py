"""
Question Extractor for parsing Pearson papers and storing in database.

Extracts real question text and marking-scheme context from the Pearson IGCSE
exam PDFs using pdfplumber, optionally structuring the messy PDF text into clean
question objects with Claude. Results are persisted as PaperQuestion rows and
cached to JSON so the quiz generator can few-shot on authentic Pearson questions.
"""

import json
import logging
import os
import re
from pathlib import Path
from typing import List, Dict, Optional, Any

from sqlalchemy.orm import Session as DBSession

from src.database.models import PaperQuestion

logger = logging.getLogger(__name__)


# Default source directory, overridable via env for portability/deployment.
DEFAULT_PAPERS_DIR = os.getenv(
    "PEARSON_PAPERS_DIR", r"C:\Users\chiny\Downloads\pearson papers"
)

# Where the structured, few-shot-ready questions are cached for the generator.
DEFAULT_CACHE_JSON = os.path.join("data", "pearson_questions.json")

# Map the quiz generator's subject keys to the reference manager's subject names.
GENERATOR_SUBJECT_MAP = {
    "maths": ["Maths"],
    "english": ["English Language", "English Literature"],
    "science": ["Science", "Biology", "Chemistry", "Physics"],
    "french": ["French"],
    "finearts": [],
}


def reference_to_generator_subject(ref_subject: str) -> str:
    """Map a reference-manager subject name to a generator subject key."""
    for gen, refs in GENERATOR_SUBJECT_MAP.items():
        if ref_subject in refs:
            return gen
    return (ref_subject or "").lower()


class PearsonQuestionExtractor:
    """Extracts real questions from Pearson papers via pdfplumber (+ optional LLM)."""

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

    # ----- Heuristics (also used as validation / fallback) -----

    @staticmethod
    def infer_difficulty(question_text: str) -> str:
        """Infer difficulty level from question text using command words."""
        question_lower = (question_text or "").lower()
        for word, difficulty in PearsonQuestionExtractor.COMMAND_WORDS.items():
            if word in question_lower:
                return difficulty
        return "medium"

    @staticmethod
    def detect_command_word(question_text: str) -> str:
        """Return the first Edexcel command word found in the text, if any."""
        lower = (question_text or "").lower()
        for word in PearsonQuestionExtractor.COMMAND_WORDS:
            if re.search(rf"\b{word}\b", lower):
                return word
        return ""

    @staticmethod
    def extract_marks(question_text: str) -> Optional[int]:
        """Extract a marks total if present (e.g. '[/5]', '(3 marks)', 'Marks: 4')."""
        patterns = [
            r"\[\s*/?\s*(\d+)\s*\]",
            r"\((\d+)\s*marks?\)",
            r"marks?\s*[:\-]?\s*(\d+)",
        ]
        for pat in patterns:
            m = re.search(pat, question_text or "", re.IGNORECASE)
            if m:
                try:
                    return int(m.group(1))
                except (ValueError, TypeError):
                    continue
        return None

    @staticmethod
    def parse_multiple_choice_options(text: str) -> Optional[List[str]]:
        """Parse multiple choice options from text (A) ... or 1) ...)."""
        lines = [line.strip() for line in (text or "").split("\n") if line.strip()]

        options: List[str] = []
        for line in lines:
            match = re.match(r"^[A-D]\)\s+(.+)$", line)
            if match:
                options.append(match.group(1).strip())
        if len(options) == 4:
            return options

        options = []
        for line in lines:
            match = re.match(r"^[1-4]\)\s+(.+)$", line)
            if match:
                options.append(match.group(1).strip())
        return options if len(options) == 4 else None

    # ----- PDF text extraction -----

    @staticmethod
    def extract_text_from_pdf(filepath: str, max_pages: int = 12) -> str:
        """Extract text from the first `max_pages` pages of a PDF via pdfplumber."""
        try:
            import pdfplumber
        except ImportError:
            logger.error("pdfplumber is not installed; cannot extract PDF text")
            return ""

        text_parts: List[str] = []
        try:
            with pdfplumber.open(filepath) as pdf:
                for page in pdf.pages[:max_pages]:
                    page_text = page.extract_text() or ""
                    if page_text.strip():
                        text_parts.append(page_text)
        except Exception as e:
            logger.error(f"Failed to extract text from {filepath}: {e}")
            return ""

        return "\n".join(text_parts)

    # ----- Structuring: LLM (preferred) with regex fallback -----

    @staticmethod
    def structure_questions_with_llm(
        paper_text: str,
        subject: str,
        paper_code: str,
        max_questions: int = 15,
    ) -> List[Dict[str, Any]]:
        """Use Claude to structure raw exam text into clean question objects."""
        if not paper_text.strip():
            return []
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            logger.warning("ANTHROPIC_API_KEY not set; skipping LLM structuring")
            return []

        try:
            from anthropic import Anthropic

            client = Anthropic(api_key=api_key)
            system = (
                "You extract exam questions from raw Pearson/Edexcel IGCSE exam paper text. "
                "Return ONLY a JSON array (no markdown, no prose). Each element must have: "
                '"question_number" (int), "question_text" (string, the full question stem), '
                '"command_word" (string, e.g. explain/calculate/describe or ""), '
                '"topic" (short string), "marks" (int or null), '
                '"question_type" (one of "short_answer", "essay", "multiple_choice", "calculation"). '
                "Skip instructions, cover pages, and formulae sheets; only include real questions."
            )
            user = (
                f"Subject: {subject}\nPaper code: {paper_code}\n"
                f"Extract up to {max_questions} questions from this exam text:\n\n"
                f"{paper_text[:15000]}"
            )
            response = client.messages.create(
                model="claude-opus-4-8",
                max_tokens=3000,
                system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
                messages=[{"role": "user", "content": user}],
            )
            raw = response.content[0].text
            return PearsonQuestionExtractor._parse_json_array(raw)[:max_questions]
        except Exception as e:
            logger.warning(f"LLM structuring failed for {paper_code}: {e}")
            return []

    @staticmethod
    def _parse_json_array(raw: str) -> List[Dict[str, Any]]:
        """Robustly parse a JSON array out of a (possibly noisy) model response."""
        if not raw:
            return []
        text = raw.strip()
        # Strip markdown code fences if present.
        text = re.sub(r"^```(?:json)?", "", text).strip()
        text = re.sub(r"```$", "", text).strip()
        # Grab the outermost array.
        start, end = text.find("["), text.rfind("]")
        if start != -1 and end != -1 and end > start:
            text = text[start : end + 1]
        try:
            data = json.loads(text)
            return data if isinstance(data, list) else []
        except json.JSONDecodeError as e:
            logger.warning(f"Could not parse structured questions JSON: {e}")
            return []

    @staticmethod
    def structure_questions_regex(
        paper_text: str, max_questions: int = 15
    ) -> List[Dict[str, Any]]:
        """Fallback: split exam text into questions using number markers."""
        if not paper_text.strip():
            return []

        # Split on line-leading question numbers like "1 " / "2." / "3)".
        chunks = re.split(r"\n\s*(\d{1,2})[\.\)]?\s+", "\n" + paper_text)
        questions: List[Dict[str, Any]] = []
        # chunks: ['', '1', 'text', '2', 'text', ...]
        for i in range(1, len(chunks) - 1, 2):
            try:
                q_num = int(chunks[i])
            except (ValueError, TypeError):
                continue
            body = chunks[i + 1].strip()
            if len(body) < 20:  # skip noise
                continue
            # Skip formula sheets / symbol pages: pdfplumber emits "(cid:NN)" for
            # glyphs it can't map, which cluster on equation/reference pages.
            if body.count("(cid:") >= 2:
                continue
            # Keep only chunks that look like real questions.
            lower = body.lower()
            has_signal = (
                "?" in body
                or "marks" in lower
                or PearsonQuestionExtractor.detect_command_word(body) != ""
            )
            if not has_signal:
                continue
            body = body[:600]
            questions.append(
                {
                    "question_number": q_num,
                    "question_text": body,
                    "command_word": PearsonQuestionExtractor.detect_command_word(body),
                    "topic": "",
                    "marks": PearsonQuestionExtractor.extract_marks(body),
                    "question_type": "short_answer",
                }
            )
            if len(questions) >= max_questions:
                break
        return questions

    # ----- Import orchestration -----

    @staticmethod
    def import_papers_to_database(
        db: DBSession,
        papers_dir: str = DEFAULT_PAPERS_DIR,
        use_llm: bool = True,
        cache_json_path: str = DEFAULT_CACHE_JSON,
    ) -> Dict[str, int]:
        """Extract real questions from every exam paper and persist them.

        Replaces any existing rows for each source file (idempotent re-runs),
        pairs each subject's questions with a marking-scheme excerpt, and writes
        a JSON cache of few-shot examples keyed by generator subject.
        """
        from src.papers.reference_manager import PaperReference, PaperReferenceManager

        manager = PaperReferenceManager(papers_dir)
        manager.scan_directory()

        stats = {"papers_processed": 0, "questions_created": 0, "errors": 0}
        cache: Dict[str, List[Dict[str, Any]]] = {}

        for ref_subject, papers in manager.get_all_papers_by_subject().items():
            gen_subject = reference_to_generator_subject(ref_subject)

            # A marking-scheme excerpt used as context for this subject's questions.
            scheme_excerpt = ""
            schemes = manager.get_marking_schemes_for_subject(ref_subject)
            if schemes:
                scheme_text = PearsonQuestionExtractor.extract_text_from_pdf(
                    schemes[0]["filepath"], max_pages=6
                )
                scheme_excerpt = scheme_text[:1500]

            for paper in papers:
                try:
                    text = PearsonQuestionExtractor.extract_text_from_pdf(paper["filepath"])
                    if not text.strip():
                        logger.warning(f"No text extracted from {paper['filename']}")
                        stats["errors"] += 1
                        continue

                    questions: List[Dict[str, Any]] = []
                    if use_llm:
                        questions = PearsonQuestionExtractor.structure_questions_with_llm(
                            text, ref_subject, paper["paper_code"]
                        )
                    if not questions:
                        questions = PearsonQuestionExtractor.structure_questions_regex(text)

                    if not questions:
                        logger.warning(f"No questions parsed from {paper['filename']}")
                        stats["errors"] += 1
                        continue

                    # Idempotent: drop any prior rows for this source file.
                    db.query(PaperQuestion).filter_by(
                        source_filename=paper["filename"]
                    ).delete()

                    for q in questions:
                        q_text = (q.get("question_text") or "").strip()
                        if not q_text:
                            continue
                        command_word = q.get("command_word") or PearsonQuestionExtractor.detect_command_word(q_text)
                        topic = q.get("topic") or ""
                        difficulty = PearsonQuestionExtractor.infer_difficulty(
                            f"{command_word} {q_text}"
                        )
                        marks = q.get("marks")
                        if isinstance(marks, str):
                            marks = PearsonQuestionExtractor.extract_marks(marks)

                        record = PaperQuestion(
                            paper_code=paper["paper_code"],
                            paper_number=paper["paper_number"] or 1,
                            subject=ref_subject,
                            question_number=q.get("question_number") or 0,
                            question_text=q_text,
                            question_type=q.get("question_type") or "short_answer",
                            options_json=json.dumps({"command_word": command_word, "topic": topic}),
                            correct_answer=None,
                            marking_scheme=scheme_excerpt or None,
                            marks_total=marks if isinstance(marks, int) else None,
                            source_filename=paper["filename"],
                            difficulty_level=difficulty,
                        )
                        db.add(record)
                        stats["questions_created"] += 1

                        if gen_subject:
                            cache.setdefault(gen_subject, []).append(
                                {
                                    "question_text": q_text[:400],
                                    "command_word": command_word,
                                    "topic": topic,
                                    "marks": marks if isinstance(marks, int) else None,
                                    "difficulty": difficulty,
                                    "source": paper["filename"],
                                }
                            )

                    db.commit()
                    stats["papers_processed"] += 1
                    logger.info(
                        f"Imported {len(questions)} questions from {paper['filename']}"
                    )

                except Exception as e:
                    db.rollback()
                    logger.error(f"Error processing {paper['filename']}: {e}")
                    stats["errors"] += 1

        # Write few-shot cache for the quiz generator.
        try:
            cache_path = Path(cache_json_path)
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")
            logger.info(f"Wrote Pearson question cache to {cache_path}")
        except Exception as e:
            logger.error(f"Failed to write Pearson question cache: {e}")

        logger.info(
            f"Import complete: {stats['papers_processed']} papers, "
            f"{stats['questions_created']} questions, {stats['errors']} errors"
        )
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
        difficulty_level: str = "medium",
    ) -> PaperQuestion:
        """Add a manually entered/corrected question to the database."""
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
            difficulty_level=difficulty_level
            or PearsonQuestionExtractor.infer_difficulty(question_text),
        )
        db.add(question)
        db.commit()
        logger.info(f"Added question {question_number} from {paper_code} Paper {paper_number}")
        return question
