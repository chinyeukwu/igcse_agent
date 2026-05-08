"""
Response validation and guardrails.
Ensures LLM responses stay on-topic and don't leak system information.
Follows SonarQube standards S3330, S4502.
"""

import logging
import json
import re
from typing import Tuple, Optional

logger = logging.getLogger(__name__)

# ===== Response Validation Rules =====

# Patterns that indicate response leakage of system prompt
LEAKAGE_PATTERNS = [
    r"system\s*prompt",
    r"you\s*are\s*instructed",
    r"your\s*instructions",
    r"my\s*instructions",
    r"the\s*prompt",
    r"administrator|admin",
    r"model.*instruction",
    r"override.*rule",
]

# Inappropriate response patterns
INAPPROPRIATE_PATTERNS = [
    r"(cannot|can't|won't)\s*help",  # Overly restrictive responses
    r"i\s*cannot\s+assist",
    r"illegal|dangerous|harmful",  # Responses that go too technical on restrictions
]

# Off-topic indicators
OFF_TOPIC_PATTERNS = [
    r"stock\s*market|cryptocurrency|investing",
    r"dating|romance|relationship",
    r"political|politics|government",
    r"religion|god|faith",
    r"drug|alcohol|smoking|violence",
]

# On-topic quality indicators
ON_TOPIC_PATTERNS = [
    r"igcse|edexcel|curriculum",
    r"chapter|unit|topic",
    r"key.*point|concept|principle",
    r"example|illustration|case",
    r"revision|examination|exam",
    r"question|answer|solution",
]


class ResponseValidator:
    """Validates LLM responses for appropriateness and accuracy."""

    @staticmethod
    def validate_response(response: str, subject: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """
        Validate LLM response for security and quality issues.

        Args:
            response: LLM response text
            subject: IGCSE subject (optional, for context)

        Returns:
            Tuple of (is_valid: bool, error_message: Optional[str])
        """
        if not response or not isinstance(response, str):
            return False, "Response is invalid"

        if len(response) > 10000:
            return False, "Response exceeds maximum length"

        if len(response) < 20:
            return False, "Response is too short"

        # Check for system prompt leakage
        is_leakage, leakage_msg = ResponseValidator._detect_leakage(response)
        if is_leakage:
            logger.warning(f"System prompt leakage detected: {leakage_msg}")
            return False, "Response contains invalid information"

        # Check for inappropriate content
        is_inappropriate, inapp_msg = ResponseValidator._detect_inappropriate(response)
        if is_inappropriate:
            logger.warning(f"Inappropriate response detected: {inapp_msg}")
            return False, "Response contains inappropriate content"

        # Check for off-topic content
        is_off_topic, offtopic_msg = ResponseValidator._detect_off_topic(response)
        if is_off_topic:
            logger.warning(f"Off-topic response detected: {offtopic_msg}")
            return False, "Response is not related to IGCSE subjects"

        return True, None

    @staticmethod
    def validate_json_response(response: str) -> Tuple[bool, Optional[dict], Optional[str]]:
        """
        Validate and parse JSON-formatted LLM response.

        Args:
            response: JSON response text from LLM

        Returns:
            Tuple of (is_valid: bool, parsed_data: Optional[dict], error_message: Optional[str])
        """
        try:
            # Extract JSON from response (in case there's extra text)
            json_match = re.search(r"\{.*\}", response, re.DOTALL)
            if not json_match:
                return False, None, "No JSON found in response"

            json_str = json_match.group()
            data = json.loads(json_str)

            # Validate structure
            if not isinstance(data, dict):
                return False, None, "Invalid JSON structure"

            # Check required fields
            if "answer" in data:
                if not isinstance(data["answer"], dict):
                    return False, None, "Answer field must be an object"

                answer = data["answer"]
                if "key_points" not in answer or "conclusion" not in answer:
                    return False, None, "Missing required fields in answer"

                if not isinstance(answer["key_points"], list):
                    return False, None, "Key points must be a list"

                if not isinstance(answer["conclusion"], str):
                    return False, None, "Conclusion must be a string"

            return True, data, None

        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {str(e)}")
            return False, None, "Invalid JSON format"
        except Exception as e:
            logger.error(f"Response validation error: {str(e)}")
            return False, None, "Response validation failed"

    @staticmethod
    def _detect_leakage(response: str) -> Tuple[bool, Optional[str]]:
        """
        Detect if response leaks system prompt or internal instructions.

        Args:
            response: Response text

        Returns:
            Tuple of (has_leakage: bool, reason: Optional[str])
        """
        response_lower = response.lower()

        for pattern in LEAKAGE_PATTERNS:
            if re.search(pattern, response_lower):
                # Double-check it's not legitimate educational mention
                if "system prompt" in response_lower and "igcse" in response_lower:
                    continue  # Allow if it's educational context

                return True, f"Detected system information pattern: {pattern}"

        # Check for escaped template markers
        if "{{" in response or "}}" in response or "{%" in response:
            return True, "Detected template markers"

        return False, None

    @staticmethod
    def _detect_inappropriate(response: str) -> Tuple[bool, Optional[str]]:
        """
        Detect inappropriate response content.

        Args:
            response: Response text

        Returns:
            Tuple of (is_inappropriate: bool, reason: Optional[str])
        """
        response_lower = response.lower()

        # Check for overly restrictive responses (signs of jailbreak attempt)
        for pattern in INAPPROPRIATE_PATTERNS:
            if re.search(pattern, response_lower):
                # Allow if it's a legitimate boundary statement
                if "cannot" in response_lower and "igcse" in response_lower:
                    continue

                return True, f"Detected potentially problematic pattern: {pattern}"

        # Check for harmful content
        harmful_keywords = [
            "violence",
            "abuse",
            "illegal activity",
            "weapon",
            "drug distribution",
            "hacking",
            "hack",
            "sql injection",
            "exploit",
        ]

        for keyword in harmful_keywords:
            if keyword in response_lower:
                return True, f"Detected harmful content: {keyword}"

        return False, None

    @staticmethod
    def _detect_off_topic(response: str) -> Tuple[bool, Optional[str]]:
        """
        Detect if response is off-topic for IGCSE.

        Args:
            response: Response text

        Returns:
            Tuple of (is_off_topic: bool, reason: Optional[str])
        """
        response_lower = response.lower()

        # Check for explicit off-topic content
        for pattern in OFF_TOPIC_PATTERNS:
            if re.search(pattern, response_lower):
                # Check if this is mentioned in educational context
                if "igcse" in response_lower or "curriculum" in response_lower:
                    continue  # Allowed

                return True, f"Detected off-topic content: {pattern}"

        # Check if response has on-topic indicators
        has_on_topic = any(re.search(pattern, response_lower) for pattern in ON_TOPIC_PATTERNS)

        # If response is very generic without on-topic markers, might be suspicious
        if not has_on_topic and len(response) < 100:
            generic_keywords = [
                "i'm not sure",
                "i don't know",
                "cannot help",
                "out of scope",
            ]

            if any(keyword in response_lower for keyword in generic_keywords):
                return True, "Response appears dismissive without educational value"

        return False, None

    @staticmethod
    def score_response_quality(response: str) -> float:
        """
        Score response quality (0-1 scale).

        Args:
            response: Response text

        Returns:
            Quality score (0.0 = poor, 1.0 = excellent)
        """
        score = 0.5  # Start at neutral

        response_lower = response.lower()

        # Penalize if very short
        if len(response) < 50:
            score -= 0.2
        elif len(response) > 2000:
            score -= 0.1
        else:
            score += 0.1

        # Reward structured responses
        if "firstly" in response_lower or "first," in response_lower:
            score += 0.1
        if "key point" in response_lower or "conclusion" in response_lower:
            score += 0.1
        if "example" in response_lower or "for instance" in response_lower:
            score += 0.1

        # Penalize if too generic
        if response_lower.count("not sure") > 0:
            score -= 0.1

        # Reward on-topic indicators
        on_topic_count = sum(1 for pattern in ON_TOPIC_PATTERNS if re.search(pattern, response_lower))
        score += min(0.2, on_topic_count * 0.05)

        return max(0.0, min(1.0, score))

    @staticmethod
    def truncate_response(response: str, max_length: int = 2000) -> str:
        """
        Truncate response to safe length.

        Args:
            response: Response text
            max_length: Maximum length

        Returns:
            Truncated response with ellipsis if needed
        """
        if len(response) <= max_length:
            return response

        # Try to truncate at sentence boundary
        truncated = response[:max_length]
        last_period = truncated.rfind(".")

        if last_period > max_length - 100:
            return truncated[:last_period + 1]

        return truncated + "..."
