"""
One-time seed script: extract real questions from the Pearson IGCSE exam PDFs
into the database and write the few-shot cache used by the quiz generator.

Usage (from the repo root, with the venv active):
    python -m scripts.extract_pearson
    python -m scripts.extract_pearson --papers-dir "C:\\path\\to\\pearson papers"
    python -m scripts.extract_pearson --no-llm      # regex-only, no Claude calls

Set ANTHROPIC_API_KEY for higher-quality LLM structuring. Without it (or with
--no-llm) the script falls back to regex extraction. Re-running is idempotent:
rows for each source file are replaced.
"""

import argparse
import logging
import os
import sys

# Ensure the project root is importable when run as a plain script.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import init_database, get_session
from src.papers.question_extractor import (
    PearsonQuestionExtractor,
    DEFAULT_PAPERS_DIR,
    DEFAULT_CACHE_JSON,
)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="Extract Pearson exam questions.")
    parser.add_argument("--papers-dir", default=DEFAULT_PAPERS_DIR)
    parser.add_argument("--cache-json", default=DEFAULT_CACHE_JSON)
    parser.add_argument("--no-llm", action="store_true", help="Skip Claude structuring")
    args = parser.parse_args()

    if not os.path.isdir(args.papers_dir):
        print(f"ERROR: papers directory not found: {args.papers_dir}")
        return 1

    print(f"Initializing database and extracting from: {args.papers_dir}")
    init_database()
    db = get_session()

    use_llm = not args.no_llm and bool(os.getenv("ANTHROPIC_API_KEY"))
    if not use_llm:
        print("Structuring mode: regex fallback (no LLM)")
    else:
        print("Structuring mode: Claude + regex fallback")

    stats = PearsonQuestionExtractor.import_papers_to_database(
        db,
        papers_dir=args.papers_dir,
        use_llm=use_llm,
        cache_json_path=args.cache_json,
    )

    print("\n=== Extraction complete ===")
    print(f"  Papers processed : {stats['papers_processed']}")
    print(f"  Questions created: {stats['questions_created']}")
    print(f"  Errors           : {stats['errors']}")
    print(f"  Cache written to : {args.cache_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
