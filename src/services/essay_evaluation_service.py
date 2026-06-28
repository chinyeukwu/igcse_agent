"""
Essay Evaluation Service - Uses Claude API to score essay-type answers.
"""

import logging
import json
from typing import Dict, Any, Tuple
from anthropic import Anthropic

logger = logging.getLogger(__name__)


class EssayEvaluationService:
    """Evaluates essay-type answers using Claude API."""

    _client = None

    @classmethod
    def get_client(cls) -> Anthropic:
        """Get or create Anthropic client."""
        if cls._client is None:
            import os
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY environment variable not set")
            cls._client = Anthropic(api_key=api_key)
        return cls._client

    @staticmethod
    def evaluate_essay(
        student_essay: str,
        question_text: str,
        model_answer: str,
        marking_scheme: str,
        marks_total: int = 10,
        subject: str = "English",
        difficulty: str = "medium"
    ) -> Tuple[float, str, Dict[str, Any]]:
        """
        Evaluate a student's essay answer using Claude.

        Args:
            student_essay: Student's written response
            question_text: The essay question
            model_answer: Official model answer/expected response
            marking_scheme: Detailed marking criteria
            marks_total: Total marks available
            subject: Subject (English, History, etc.)
            difficulty: Difficulty level (easy, medium, hard)

        Returns:
            Tuple of (score_earned, feedback, detailed_rubric)
        """
        client = EssayEvaluationService.get_client()

        evaluation_prompt = f"""You are an expert {subject} examiner marking IGCSE student essays.

QUESTION:
{question_text}

STUDENT'S ANSWER:
{student_essay}

MODEL ANSWER/GUIDANCE:
{model_answer}

MARKING SCHEME:
{marking_scheme}

TASK:
Evaluate the student's essay against the marking scheme and model answer.
Provide:
1. A score out of {marks_total} marks
2. Detailed feedback on strengths and weaknesses
3. Specific areas for improvement
4. Citation of exact marking criteria used

RESPOND WITH ONLY VALID JSON (no markdown, no code blocks):
{{
    "score": <float 0-{marks_total}>,
    "percentage": <float 0-100>,
    "strengths": ["strength1", "strength2", ...],
    "weaknesses": ["weakness1", "weakness2", ...],
    "feedback": "detailed constructive feedback",
    "improvement_areas": ["area1", "area2", ...],
    "marking_criteria_used": "which criteria from scheme were applied",
    "rubric_breakdown": {{
        "content_knowledge": {{"score": X, "max": Y, "comment": "..."}},
        "analysis_critical_thinking": {{"score": X, "max": Y, "comment": "..."}},
        "communication_clarity": {{"score": X, "max": Y, "comment": "..."}},
        "structure_organization": {{"score": X, "max": Y, "comment": "..."}}
    }}
}}"""

        try:
            response = client.messages.create(
                model="claude-opus-4-7",
                max_tokens=1500,
                messages=[
                    {
                        "role": "user",
                        "content": evaluation_prompt
                    }
                ]
            )

            response_text = response.content[0].text

            # Parse JSON response
            try:
                result = json.loads(response_text)
            except json.JSONDecodeError:
                # Try to extract JSON if wrapped in markdown
                import re
                json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group(1))
                else:
                    json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                    if json_match:
                        result = json.loads(json_match.group(0))
                    else:
                        raise ValueError("Could not parse Claude response as JSON")

            # Validate response
            score = float(result.get("score", 0))
            score = min(max(score, 0), marks_total)  # Clamp to valid range

            feedback = result.get("feedback", "No feedback provided")
            detailed_rubric = {
                "strengths": result.get("strengths", []),
                "weaknesses": result.get("weaknesses", []),
                "improvement_areas": result.get("improvement_areas", []),
                "marking_criteria_used": result.get("marking_criteria_used", ""),
                "rubric_breakdown": result.get("rubric_breakdown", {}),
            }

            logger.info(f"Essay evaluated: {score}/{marks_total} ({result.get('percentage', 0):.1f}%)")
            return score, feedback, detailed_rubric

        except Exception as e:
            logger.error(f"Essay evaluation error: {str(e)}")
            # Fallback: return zero score with error message
            return 0.0, f"Error evaluating essay: {str(e)}", {
                "strengths": [],
                "weaknesses": ["Could not evaluate essay"],
                "improvement_areas": [],
                "error": str(e)
            }

    @staticmethod
    def generate_essay_rubric(
        question_text: str,
        subject: str = "English",
        marks_total: int = 10
    ) -> Dict[str, Any]:
        """
        Generate a marking rubric for an essay question using Claude.

        Args:
            question_text: The essay question
            subject: Subject
            marks_total: Total marks available

        Returns:
            Rubric with criteria and mark allocations
        """
        client = EssayEvaluationService.get_client()

        rubric_prompt = f"""Create a detailed IGCSE marking rubric for this {subject} essay question.

QUESTION:
{question_text}

TASK:
Generate a comprehensive marking rubric with {marks_total} total marks allocated across criteria.
Structure with: Content Knowledge, Analysis/Critical Thinking, Communication/Clarity, Structure/Organization

RESPOND WITH ONLY VALID JSON (no markdown):
{{
    "question_summary": "brief summary",
    "total_marks": {marks_total},
    "criteria": {{
        "content_knowledge": {{
            "marks": X,
            "descriptor": "...",
            "exemplars": ["exemplar1", "exemplar2"]
        }},
        "analysis_critical_thinking": {{...}},
        "communication_clarity": {{...}},
        "structure_organization": {{...}}
    }},
    "common_mistakes": ["mistake1", "mistake2"],
    "band_descriptors": {{
        "excellent": {{"range": "8-10", "descriptor": "..."}},
        "good": {{"range": "6-7", "descriptor": "..."}},
        "satisfactory": {{"range": "4-5", "descriptor": "..."}},
        "needs_improvement": {{"range": "0-3", "descriptor": "..."}}
    }}
}}"""

        try:
            response = client.messages.create(
                model="claude-opus-4-7",
                max_tokens=2000,
                messages=[
                    {
                        "role": "user",
                        "content": rubric_prompt
                    }
                ]
            )

            response_text = response.content[0].text
            rubric = json.loads(response_text)
            logger.info(f"Generated rubric for essay: {rubric.get('question_summary', 'unknown')}")
            return rubric

        except Exception as e:
            logger.error(f"Rubric generation error: {str(e)}")
            return {"error": str(e), "total_marks": marks_total}
