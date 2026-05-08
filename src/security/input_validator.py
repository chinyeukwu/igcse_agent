"""
Input validation and prompt injection detection.
Follows SonarQube standards S4502 (CWE-79), S3330 (prompt injection prevention).
"""

import logging
import re
from typing import Tuple, Optional

logger = logging.getLogger(__name__)

# ===== Prompt Injection Detection Patterns =====

# Common jailbreak/injection keywords (case-insensitive)
JAILBREAK_KEYWORDS = [
    "forget",
    "ignore previous",
    "override",
    "bypass",
    "disregard",
    "system prompt",
    "prompt injection",
    "prompt jailbreak",
    "jailbreak",
    "act as",
    "pretend",
    "roleplay",
    "assume you are",
    "you are now",
    "from now on",
    "new instruction",
    "administrator",
    "sudo",
    "execute",
    "run command",
    "shell command",
    "sql injection",
    "script tag",
    "javascript",
    "<script",
    "' or '",
    "'; drop",
    "union select",
    "1=1",
]

# Out-of-scope keywords (not IGCSE subjects)
OUT_OF_SCOPE_KEYWORDS = [
    "hack",
    "bomb",
    "drug",
    "weapon",
    "virus",
    "malware",
    "exploit",
    "cryptocurrency",
    "stock market",
    "gambling",
    "adult",
    "dating",
    "politics",
    "religion",
]

# IGCSE-aligned subjects (whitelist)
IGCSE_SUBJECTS = [
    "english",
    "english language",
    "english literature",
    "mathematics",
    "maths",
    "math",
    "science",
    "double award",
    "double award science",
    "biology",
    "chemistry",
    "physics",
    "french",
    "fine art",
    "fine arts",
    "art",
]


class InputValidator:
    """Validates user input for security threats and out-of-scope queries."""

    @staticmethod
    def validate_query(query: str, max_length: int = 1000) -> Tuple[bool, Optional[str]]:
        """
        Validate user query for security and scope issues.

        Args:
            query: User query text
            max_length: Maximum query length in characters

        Returns:
            Tuple of (is_valid: bool, error_message: Optional[str])
        """
        if not query or not isinstance(query, str):
            return False, "Query must be a non-empty string"

        # Check length
        if len(query) > max_length:
            return False, f"Query exceeds maximum length of {max_length} characters"

        if len(query) < 3:
            return False, "Query must be at least 3 characters"

        # Check for injection attempts
        is_injection, injection_msg = InputValidator._detect_injection(query)
        if is_injection:
            logger.warning(f"Injection attempt detected: {injection_msg}")
            return False, "Your query contains suspicious patterns. Please try a different approach."

        # Check for out-of-scope topics
        is_out_of_scope, scope_msg = InputValidator._check_scope(query)
        if is_out_of_scope:
            logger.info(f"Out-of-scope query: {scope_msg}")
            return False, "I can only help with IGCSE subjects: English, Maths, Science, French, and Fine Arts."

        return True, None

    @staticmethod
    def _detect_injection(query: str) -> Tuple[bool, Optional[str]]:
        """
        Detect common prompt injection and jailbreak attempts.

        Args:
            query: User query text

        Returns:
            Tuple of (has_injection: bool, detection_reason: Optional[str])
        """
        query_lower = query.lower()

        # Check for jailbreak keywords
        for keyword in JAILBREAK_KEYWORDS:
            if keyword in query_lower:
                # Count occurrences to avoid false positives
                if query_lower.count(keyword) >= 1:
                    # Skip if it's a legitimate educational question
                    if not InputValidator._is_educational_context(query, keyword):
                        return True, f"Detected instruction override attempt: '{keyword}'"

        # Check for SQL injection patterns
        sql_patterns = [
            r"'\s*OR\s*'",
            r";\s*DROP",
            r"UNION\s+SELECT",
            r"--\s*$",
            r"/\*.*\*/",
        ]
        for pattern in sql_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                return True, f"Detected SQL injection pattern: {pattern}"

        # Check for script injection patterns
        if re.search(r"<script|javascript:|onerror=|onload=", query, re.IGNORECASE):
            return True, "Detected script injection pattern"

        # Check for command injection patterns
        if re.search(r"\$\(|`|&&|;|\||>\s*|<\s*", query):
            # Allow these in educational context (math, logic)
            if not InputValidator._is_educational_context(query, "command"):
                return True, "Detected command injection pattern"

        return False, None

    @staticmethod
    def _is_educational_context(query: str, keyword: str) -> bool:
        """
        Check if a potentially suspicious keyword is in legitimate educational context.

        Args:
            query: User query text
            keyword: Suspicious keyword

        Returns:
            True if context is educational, False otherwise
        """
        query_lower = query.lower()

        # Allow certain keywords in educational contexts
        educational_contexts = {
            "command": [
                "command economy",
                "command structure",
                "command line",
            ],
            "$": [
                "cost",
                "function",
                "variable",
            ],
            ";": [
                "semicolon",
                "grammatically",
            ],
        }

        if keyword in educational_contexts:
            for context in educational_contexts[keyword]:
                if context in query_lower:
                    return True

        return False

    @staticmethod
    def _check_scope(query: str) -> Tuple[bool, Optional[str]]:
        """
        Check if query is within IGCSE scope.

        Args:
            query: User query text

        Returns:
            Tuple of (is_out_of_scope: bool, reason: Optional[str])
        """
        query_lower = query.lower()

        # Check for dangerous topics
        for dangerous_keyword in OUT_OF_SCOPE_KEYWORDS:
            if dangerous_keyword in query_lower:
                return True, f"Query contains out-of-scope topic: {dangerous_keyword}"

        # Try to identify subject from query
        subject_found = False
        for subject in IGCSE_SUBJECTS:
            if subject in query_lower:
                subject_found = True
                break

        # If no IGCSE subject mentioned, query might be out of scope
        # But allow it if query has academic keywords
        academic_keywords = [
            "what",
            "how",
            "why",
            "explain",
            "define",
            "describe",
            "analyze",
            "calculate",
            "solve",
            "theorem",
            "law",
            "principle",
            "concept",
            "chapter",
            "exam",
            "test",
            "question",
            "revision",
            "study",
            "homework",
        ]

        has_academic_keyword = any(keyword in query_lower for keyword in academic_keywords)

        if not subject_found and not has_academic_keyword:
            return True, "Query does not appear to be IGCSE-related"

        return False, None

    @staticmethod
    def sanitize_query(query: str) -> str:
        """
        Sanitize query for safe processing.

        Args:
            query: User query text

        Returns:
            Sanitized query (limited to audit logging only)
        """
        # Remove leading/trailing whitespace
        sanitized = query.strip()

        # Limit length for storage
        max_audit_length = 500
        if len(sanitized) > max_audit_length:
            sanitized = sanitized[:max_audit_length] + "..."

        return sanitized

    @staticmethod
    def extract_subject(query: str) -> Optional[str]:
        """
        Extract IGCSE subject from query.

        Args:
            query: User query text

        Returns:
            Subject name or None
        """
        query_lower = query.lower()

        subject_mapping = {
            "english": [
                "english",
                "grammar",
                "vocabulary",
                "literature",
                "shakespeare",
                "poem",
                "novel",
                "hamlet",
                "macbeth",
                "character",
                "theme",
                "writing",
            ],
            "maths": [
                "math",
                "maths",
                "algebra",
                "geometry",
                "calculus",
                "trigonometry",
                "equation",
                "solve",
                "probability",
                "statistics",
            ],
            "science": [
                "science",
                "biology",
                "chemistry",
                "physics",
                "atom",
                "cell",
                "reaction",
                "photosynthesis",
                "enzyme",
                "force",
                "energy",
                "wave",
            ],
            "french": [
                "french",
                "français",
                "conjugate",
                "verb",
                "grammar",
                "france",
            ],
            "finearts": [
                "art",
                "fine art",
                "drawing",
                "painting",
                "design",
                "sculpture",
                "watercolor",
                "technique",
            ],
        }

        for subject, keywords in subject_mapping.items():
            for keyword in keywords:
                if keyword in query_lower:
                    return subject

        return None
