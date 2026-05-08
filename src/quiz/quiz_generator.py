"""
Quiz generator for creating fresh IGCSE quizzes using AI.
Generates question sets on-demand with configurable difficulty levels.
"""

import json
import re
from typing import List, Dict, Any, Tuple
from langchain_core.messages import HumanMessage
from src.agents.orchestrator import create_agent


class QuizGenerator:
    """Generates fresh IGCSE quizzes on-demand using LLM."""

    # Valid configurations
    VALID_SUBJECTS = ["maths", "english", "french", "science", "finearts"]
    VALID_DIFFICULTIES = ["easy", "medium", "hard"]
    VALID_QUESTION_COUNTS = [3, 5, 10]

    # Quiz prompts per subject
    SUBJECT_PROMPTS = {
        "maths": """Generate {count} {difficulty} mathematics quiz questions for IGCSE students.
Format: Return ONLY a JSON array with exactly {count} questions.
Each question must have: "question", "options" (array of 4), "correct_answer" (index 0-3), "explanation"
Difficulty: {difficulty} (easy=basic concepts, medium=multi-step, hard=complex)
""",
        "english": """Generate {count} {difficulty} English Literature quiz questions for IGCSE students.
Format: Return ONLY a JSON array with exactly {count} questions about texts, themes, and comprehension.
Each question must have: "question", "options" (array of 4), "correct_answer" (index 0-3), "explanation"
Difficulty: {difficulty}
""",
        "french": """Generate {count} {difficulty} French language quiz questions for IGCSE students.
Format: Return ONLY a JSON array with exactly {count} questions (mix of grammar, vocabulary, comprehension).
Each question must have: "question", "options" (array of 4), "correct_answer" (index 0-3), "explanation"
Questions can be in French or English. Difficulty: {difficulty}
""",
        "science": """Generate {count} {difficulty} Science quiz questions for IGCSE students (Physics, Chemistry, Biology).
Format: Return ONLY a JSON array with exactly {count} questions covering core concepts.
Each question must have: "question", "options" (array of 4), "correct_answer" (index 0-3), "explanation"
Difficulty: {difficulty}
""",
        "finearts": """Generate {count} {difficulty} Fine Arts quiz questions for IGCSE students.
Format: Return ONLY a JSON array with exactly {count} questions about techniques, history, and analysis.
Each question must have: "question", "options" (array of 4), "correct_answer" (index 0-3), "explanation"
Difficulty: {difficulty}
""",
    }

    @staticmethod
    def validate_config(
        subject: str,
        difficulty: str,
        question_count: int
    ) -> Tuple[bool, str]:
        """
        Validate quiz configuration parameters.
        
        Args:
            subject: IGCSE subject
            difficulty: Difficulty level
            question_count: Number of questions
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if subject.lower() not in QuizGenerator.VALID_SUBJECTS:
            return False, f"Invalid subject. Must be one of: {', '.join(QuizGenerator.VALID_SUBJECTS)}"
        
        if difficulty.lower() not in QuizGenerator.VALID_DIFFICULTIES:
            return False, f"Invalid difficulty. Must be one of: {', '.join(QuizGenerator.VALID_DIFFICULTIES)}"
        
        if question_count not in QuizGenerator.VALID_QUESTION_COUNTS:
            return False, f"Invalid question count. Must be one of: {', '.join(map(str, QuizGenerator.VALID_QUESTION_COUNTS))}"
        
        return True, ""

    @staticmethod
    def parse_quiz_response(response: str) -> Tuple[bool, List[Dict[str, Any]], str]:
        """
        Parse LLM response into quiz questions.
        
        Args:
            response: Raw LLM response
        
        Returns:
            Tuple of (success, questions_list, error_message)
        """
        try:
            # Try to extract JSON from response
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            
            if not json_match:
                return False, [], "Could not extract JSON from response"
            
            json_str = json_match.group(0)
            questions = json.loads(json_str)
            
            # Validate questions structure
            if not isinstance(questions, list) or len(questions) == 0:
                return False, [], "Response must contain a list of questions"
            
            # Validate each question
            for i, q in enumerate(questions):
                if not isinstance(q, dict):
                    return False, [], f"Question {i} is not a dictionary"
                
                required_fields = ["question", "options", "correct_answer", "explanation"]
                for field in required_fields:
                    if field not in q:
                        return False, [], f"Question {i} missing field: {field}"
                
                # Validate options
                if not isinstance(q["options"], list) or len(q["options"]) != 4:
                    return False, [], f"Question {i} must have exactly 4 options"
                
                # Validate correct_answer index
                if not isinstance(q["correct_answer"], int) or q["correct_answer"] not in [0, 1, 2, 3]:
                    return False, [], f"Question {i} correct_answer must be 0-3"
            
            return True, questions, ""
        
        except json.JSONDecodeError as e:
            return False, [], f"Failed to parse JSON: {str(e)}"
        except Exception as e:
            return False, [], f"Error parsing response: {str(e)}"

    @staticmethod
    def generate_quiz(
        subject: str,
        difficulty: str = "medium",
        question_count: int = 5,
        language_code: str = "en"
    ) -> Tuple[bool, List[Dict[str, Any]], str]:
        """
        Generate a fresh quiz with specified parameters.
        
        Args:
            subject: IGCSE subject (maths|english|french|science|finearts)
            difficulty: Difficulty level (easy|medium|hard)
            question_count: Number of questions (3, 5, or 10)
            language_code: Language code (default: en)
        
        Returns:
            Tuple of (success, questions, error_message)
        """
        try:
            # Validate configuration
            is_valid, error_msg = QuizGenerator.validate_config(subject, difficulty, question_count)
            if not is_valid:
                return False, [], error_msg
            
            # Get subject prompt
            subject_lower = subject.lower()
            if subject_lower not in QuizGenerator.SUBJECT_PROMPTS:
                return False, [], f"No prompt defined for subject: {subject}"
            
            # Create quiz generation prompt
            base_prompt = QuizGenerator.SUBJECT_PROMPTS[subject_lower]
            final_prompt = base_prompt.format(
                count=question_count,
                difficulty=difficulty.lower()
            )
            
            # Add strict instructions
            final_prompt += """
CRITICAL INSTRUCTIONS:
1. Return ONLY valid JSON array - no markdown, no code blocks, no extra text
2. Ensure exactly {count} questions in the array
3. Each question has exactly 4 options
4. correct_answer is a number: 0, 1, 2, or 3
5. explanation field is a string explaining the correct answer
6. No duplicate questions
""".format(count=question_count)
            
            # Generate quiz using agent
            message = HumanMessage(content=final_prompt, role="user")
            agent = create_agent()
            initial_state = {"messages": [message]}
            output = agent.invoke(initial_state)
            
            response = output["messages"][-1].content
            
            # Parse response
            success, questions, error = QuizGenerator.parse_quiz_response(response)
            
            if not success:
                return False, [], error
            
            # Verify question count
            if len(questions) != question_count:
                return False, [], f"Expected {question_count} questions, got {len(questions)}"
            
            return True, questions, ""
        
        except Exception as e:
            return False, [], f"Quiz generation error: {str(e)}"

    @staticmethod
    def generate_quiz_json(questions: List[Dict[str, Any]]) -> str:
        """
        Serialize questions list to JSON string.
        
        Args:
            questions: List of question dictionaries
        
        Returns:
            JSON string representation
        """
        try:
            return json.dumps(questions, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e)})
