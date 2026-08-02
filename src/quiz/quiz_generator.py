"""
Quiz generator for creating fresh IGCSE quizzes using AI.
Generates question sets on-demand with configurable difficulty levels.
Uses Anthropic Claude API with prompt caching for improved performance and cost efficiency.
"""

import json
import re
import random
import logging
import os
from typing import List, Dict, Any, Tuple
from anthropic import Anthropic
from src.papers.reference_manager import PaperReferenceManager

logger = logging.getLogger(__name__)


class QuizGenerator:
    """Generates fresh IGCSE quizzes on-demand using LLM with prompt caching."""

    # Valid configurations
    VALID_SUBJECTS = ["maths", "english", "french", "science", "finearts"]
    VALID_DIFFICULTIES = ["easy", "medium", "hard"]
    VALID_QUESTION_COUNTS = [3, 5, 10]

    # Initialize Claude client and paper manager
    _client = None
    _edexcel_examples = None
    _paper_manager = None
    _pearson_questions = None

    @classmethod
    def get_client(cls):
        """Lazy-load Anthropic client."""
        if cls._client is None:
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY environment variable not set")
            cls._client = Anthropic(api_key=api_key)
        return cls._client

    @classmethod
    def load_edexcel_examples(cls) -> Dict[str, Dict[str, List[Dict]]]:
        """Load cached Edexcel exam examples."""
        if cls._edexcel_examples is None:
            examples_path = os.path.join(
                os.path.dirname(__file__),
                "..",
                "assets",
                "edexcel_examples.json"
            )
            try:
                with open(examples_path, 'r') as f:
                    cls._edexcel_examples = json.load(f)
                logger.info(f"Loaded Edexcel examples from {examples_path}")
            except Exception as e:
                logger.warning(f"Could not load Edexcel examples: {str(e)}")
                cls._edexcel_examples = {}
        return cls._edexcel_examples

    @classmethod
    def get_paper_manager(cls) -> PaperReferenceManager:
        """Lazy-load paper reference manager."""
        if cls._paper_manager is None:
            cls._paper_manager = PaperReferenceManager()
            # Load cached index if available, otherwise scan directory
            index_path = os.path.join(
                os.path.dirname(__file__),
                "..",
                "..",
                "data",
                "paper_index.json"
            )
            if os.path.exists(index_path):
                cls._paper_manager.load_index(index_path)
                logger.info("Loaded paper index from cache")
            else:
                cls._paper_manager.scan_directory()
                logger.info("Scanned papers directory")
        return cls._paper_manager

    @classmethod
    def load_pearson_questions(cls) -> Dict[str, List[Dict]]:
        """Load extracted Pearson questions cached by the extraction script."""
        if cls._pearson_questions is None:
            path = os.path.join(
                os.path.dirname(__file__), "..", "..", "data", "pearson_questions.json"
            )
            try:
                with open(path, "r", encoding="utf-8") as f:
                    cls._pearson_questions = json.load(f)
                logger.info("Loaded extracted Pearson questions cache")
            except Exception:
                cls._pearson_questions = {}
        return cls._pearson_questions

    @classmethod
    def _build_pearson_questions_context(cls, subject_lower: str, max_examples: int = 4) -> str:
        """Format a few authentic Pearson questions as style context for the prompt."""
        data = cls.load_pearson_questions()
        items = data.get(subject_lower, [])
        if not items:
            return ""
        sample = items[:max_examples]
        lines = ["## Authentic Pearson Exam Questions (match this style and phrasing)"]
        for q in sample:
            marks = f" [{q['marks']} marks]" if q.get("marks") else ""
            cmd = f"({q['command_word']}) " if q.get("command_word") else ""
            lines.append(f"- {cmd}{q['question_text']}{marks}")
        return "\n".join(lines)

    # Quiz prompts per subject
    SUBJECT_PROMPTS = {
        "maths": """Generate {count} {difficulty} mathematics quiz questions for IGCSE students.

CRITICAL: Return ONLY valid JSON. No markdown, no code blocks, no extra text.

Format: JSON array with exactly {count} questions.
Each question must have these exact fields:
- "question": The question text
- "options": Array of exactly 4 answer strings
- "correct_answer": Integer index (0, 1, 2, or 3) of correct option
- "explanation": Brief explanation of the correct answer
- "workings": Step-by-step solution with calculations

Example format:
[{{"question": "...", "options": ["...", "...", "...", "..."], "correct_answer": 0, "explanation": "...", "workings": "..."}}]

Difficulty: {difficulty} (easy=basic concepts, medium=multi-step, hard=complex)
""",
        "english": """Generate {count} {difficulty} English Literature quiz questions for IGCSE students.

CRITICAL: Return ONLY valid JSON. No markdown, no code blocks, no extra text.

Format: JSON array with exactly {count} questions.
Each question must have these exact fields:
- "question": The question text
- "options": Array of exactly 4 answer strings
- "correct_answer": Integer index (0, 1, 2, or 3) of correct option
- "explanation": Brief explanation of the correct answer

Example format:
[{{"question": "...", "options": ["...", "...", "...", "..."], "correct_answer": 0, "explanation": "..."}}]

Difficulty: {difficulty}
""",
        "french": """Generate {count} {difficulty} French language quiz questions for IGCSE students.

CRITICAL: Return ONLY valid JSON. No markdown, no code blocks, no extra text.

Format: JSON array with exactly {count} questions.
Each question must have these exact fields:
- "question": The question text
- "options": Array of exactly 4 answer strings
- "correct_answer": Integer index (0, 1, 2, or 3) of correct option
- "explanation": Brief explanation of the correct answer

Difficulty: {difficulty}
""",
        "science": """Generate {count} {difficulty} Science quiz questions for IGCSE students (Physics, Chemistry, Biology).

CRITICAL: Return ONLY valid JSON. No markdown, no code blocks, no extra text.

Format: JSON array with exactly {count} questions covering core concepts.
Each question must have these exact fields:
- "question": The question text
- "options": Array of exactly 4 answer strings
- "correct_answer": Integer index (0, 1, 2, or 3) of correct option
- "explanation": Brief explanation of the correct answer

Example format:
[{{"question": "...", "options": ["...", "...", "...", "..."], "correct_answer": 0, "explanation": "..."}}]

Difficulty: {difficulty}
""",
        "finearts": """Generate {count} {difficulty} Fine Arts quiz questions for IGCSE students.

CRITICAL: Return ONLY valid JSON. No markdown, no code blocks, no extra text.

Format: JSON array with exactly {count} questions about techniques, history, and analysis.
Each question must have these exact fields:
- "question": The question text
- "options": Array of exactly 4 answer strings
- "correct_answer": Integer index (0, 1, 2, or 3) of correct option
- "explanation": Brief explanation of the correct answer

Example format:
[{{"question": "...", "options": ["...", "...", "...", "..."], "correct_answer": 0, "explanation": "..."}}]

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
    def shuffle_question_options(questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Shuffle the multiple choice options for each question.
        Updates correct_answer index to match the new option order.

        Args:
            questions: List of question dictionaries with options and correct_answer

        Returns:
            List of questions with shuffled options
        """
        shuffled_questions = []

        for question in questions:
            if "options" not in question or "correct_answer" not in question:
                shuffled_questions.append(question)
                continue

            options = question.get("options", [])
            correct_idx = question.get("correct_answer", 0)

            # Get the correct answer text
            if correct_idx < len(options):
                correct_answer_text = options[correct_idx]
            else:
                shuffled_questions.append(question)
                continue

            # Create list of (option, is_correct) tuples
            option_pairs = [(opt, opt == correct_answer_text) for opt in options]

            # Shuffle the options
            random.shuffle(option_pairs)

            # Find the new index of the correct answer
            shuffled_options = [opt for opt, _ in option_pairs]
            new_correct_idx = next(
                (i for i, (opt, is_correct) in enumerate(option_pairs) if is_correct),
                0
            )

            # Create shuffled question
            shuffled_question = question.copy()
            shuffled_question["options"] = shuffled_options
            shuffled_question["correct_answer"] = new_correct_idx

            shuffled_questions.append(shuffled_question)

        return shuffled_questions

    @staticmethod
    def parse_quiz_response(response: str) -> Tuple[bool, List[Dict[str, Any]], str]:
        """
        Parse LLM response into quiz questions.
        Handles various response formats including markdown code blocks.

        Args:
            response: Raw LLM response

        Returns:
            Tuple of (success, questions_list, error_message)
        """
        try:
            # Remove markdown code blocks if present
            cleaned_response = response
            if "```json" in cleaned_response:
                # Extract content between ```json and ```
                match = re.search(r'```json\s*(.*?)\s*```', cleaned_response, re.DOTALL)
                if match:
                    cleaned_response = match.group(1)
            elif "```" in cleaned_response:
                # Extract content between ``` and ```
                match = re.search(r'```\s*(.*?)\s*```', cleaned_response, re.DOTALL)
                if match:
                    cleaned_response = match.group(1)

            # Try to extract JSON array from response
            # Find the opening [ and matching closing ]
            start_idx = cleaned_response.find('[')
            if start_idx == -1:
                return False, [], "Could not find JSON array start in response"

            # Find the closing bracket, accounting for nested structures
            bracket_count = 0
            end_idx = -1
            for i in range(start_idx, len(cleaned_response)):
                if cleaned_response[i] == '[':
                    bracket_count += 1
                elif cleaned_response[i] == ']':
                    bracket_count -= 1
                    if bracket_count == 0:
                        end_idx = i + 1
                        break

            if end_idx == -1:
                return False, [], "Could not find JSON array end in response"

            json_str = cleaned_response[start_idx:end_idx].strip()

            # Parse JSON
            try:
                questions = json.loads(json_str)
            except json.JSONDecodeError as e:
                return False, [], f"Failed to parse JSON: {str(e)}"
            
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

    @classmethod
    def generate_quiz(
        cls,
        subject: str,
        difficulty: str = "medium",
        question_count: int = 5,
        language_code: str = "en",
        exclude_questions: set = None
    ) -> Tuple[bool, List[Dict[str, Any]], str]:
        """
        Generate a fresh quiz with specified parameters using Claude API with prompt caching.
        Falls back to sample quizzes if API is unavailable.

        Args:
            subject: IGCSE subject (maths|english|french|science|finearts)
            difficulty: Difficulty level (easy|medium|hard)
            question_count: Number of questions (3, 5, or 10)
            language_code: Language code (default: en)
            exclude_questions: Set of question texts to exclude (prevent repetition)

        Returns:
            Tuple of (success, questions, error_message)
        """
        if exclude_questions is None:
            exclude_questions = set()

        subject_lower = subject.lower()

        try:
            # Validate configuration
            is_valid, error_msg = cls.validate_config(subject, difficulty, question_count)
            if not is_valid:
                return False, [], error_msg

            if subject_lower not in cls.SUBJECT_PROMPTS:
                return False, [], f"No prompt defined for subject: {subject}"

            # Load Edexcel examples for cached system prompt
            examples = cls.load_edexcel_examples()
            edexcel_examples_text = cls._build_edexcel_examples_prompt(subject_lower, examples)

            # Load Pearson papers context
            paper_manager = cls.get_paper_manager()
            papers_context = paper_manager.get_context_for_quiz_generation(subject.title())

            # Load extracted Pearson questions as authentic few-shot style context
            pearson_questions_context = cls._build_pearson_questions_context(subject_lower)

            # Build system prompt with Edexcel examples and Pearson papers (for caching)
            system_prompt = f"""You are an expert IGCSE quiz generator specializing in Edexcel exam patterns.
Your role is to generate high-quality quiz questions that closely match Edexcel IGCSE exam standards.

{edexcel_examples_text}

{pearson_questions_context}

{papers_context}

## Guidelines for {subject.title()} Questions
- Match Edexcel's difficulty progression and question styles
- Use command words appropriate for {difficulty.title()} difficulty
- Ensure all options are plausible but clearly distinguishable
- Provide clear, concise explanations for answers
- For Maths: Always include step-by-step workings
- For English: Emphasize textual analysis and critical thinking
- Base questions on patterns observed in Pearson past papers
- Ensure questions are similar in style and difficulty to the provided papers
- Avoid trick questions; test genuine understanding"""

            # Build user prompt (dynamic, not cached)
            user_prompt = cls.SUBJECT_PROMPTS[subject_lower].format(
                count=question_count,
                difficulty=difficulty.lower()
            )

            # Add exclusion guidance if needed
            if exclude_questions:
                exclude_list = "\n".join(f"- {q[:50]}..." for q in list(exclude_questions)[:5])
                user_prompt += f"\n\nPLEASE AVOID these previously used questions:\n{exclude_list}\n\nGenerate completely fresh and different questions."

            # Call Claude API with prompt caching
            client = cls.get_client()
            response = client.messages.create(
                model="claude-opus-4-8",
                max_tokens=2000,
                system=[
                    {
                        "type": "text",
                        "text": system_prompt,
                        "cache_control": {"type": "ephemeral"}  # Cache system + examples
                    }
                ],
                messages=[
                    {
                        "role": "user",
                        "content": user_prompt  # Dynamic - not cached
                    }
                ]
            )

            response_text = response.content[0].text

            # Log cache usage
            usage = response.usage
            if hasattr(usage, 'cache_creation_input_tokens'):
                logger.info(f"Cache stats - Created: {usage.cache_creation_input_tokens}, "
                           f"Read: {usage.cache_read_input_tokens}, "
                           f"Regular: {usage.input_tokens}")

            # Parse response
            success, questions, error = cls.parse_quiz_response(response_text)

            if not success:
                return False, [], error

            # Verify question count
            if len(questions) != question_count:
                return False, [], f"Expected {question_count} questions, got {len(questions)}"

            # Shuffle the answer options
            shuffled_questions = cls.shuffle_question_options(questions)

            return True, shuffled_questions, ""

        except Exception as e:
            error_str = str(e)
            logger.error(f"Quiz generation error: {error_str}")

            # If API error, use sample questions as fallback
            if any(x in error_str.lower() for x in ["429", "quota", "rate_limit", "insufficient_quota"]):
                logger.info(f"API unavailable, falling back to sample questions for {subject_lower}")
                sample_questions = cls.get_sample_quiz(subject_lower, question_count, exclude_questions)
                if sample_questions:
                    shuffled_sample = cls.shuffle_question_options(sample_questions)
                    return True, shuffled_sample, ""
                return False, [], "Anthropic API unavailable and no sample questions available"

            return False, [], f"Quiz generation error: {error_str}"

    @staticmethod
    def _build_edexcel_examples_prompt(subject: str, examples: Dict) -> str:
        """Build cached Edexcel examples section for system prompt."""
        if subject not in examples:
            return ""

        subject_examples = examples[subject]
        examples_text = f"\n## Edexcel {subject.title()} Question Examples\n\n"

        for difficulty in ["easy", "medium", "hard"]:
            if difficulty in subject_examples:
                examples_text += f"### {difficulty.title()} Level Example:\n"
                ex = subject_examples[difficulty][0] if subject_examples[difficulty] else {}
                examples_text += f"**Q:** {ex.get('question', '')}\n"
                examples_text += f"**Options:** {', '.join(ex.get('options', []))}\n"
                examples_text += f"**Answer:** {ex.get('correct_answer', '')}\n"
                examples_text += f"**Explanation:** {ex.get('explanation', '')}\n\n"

        return examples_text

    @staticmethod
    def get_sample_quiz(subject: str, question_count: int, exclude_questions: set = None) -> List[Dict[str, Any]]:
        """
        Return sample quiz questions as fallback when API is unavailable.
        Useful for testing when OpenAI quota is exceeded.

        Args:
            subject: Subject name (maths, english, french, science, finearts)
            question_count: Number of questions (3, 5, or 10)
            exclude_questions: Set of question texts to exclude (already used)

        Returns:
            List of sample quiz questions
        """
        if exclude_questions is None:
            exclude_questions = set()
        sample_quizzes = {
            "maths": [
                {
                    "question": "What is 15 × 12?",
                    "options": ["160", "180", "200", "220"],
                    "correct_answer": 1,
                    "explanation": "15 × 12 = 180. Multiply 15 by 10 to get 150, then by 2 to get 30, then add: 150 + 30 = 180.",
                    "workings": "Step 1: Break down 15 × 12\n15 × 12 = 15 × (10 + 2)\n\nStep 2: Use distributive property\n= (15 × 10) + (15 × 2)\n= 150 + 30\n\nStep 3: Add the results\n= 180\n\nAnswer: 180"
                },
                {
                    "question": "Solve: 2x + 5 = 13",
                    "options": ["x = 2", "x = 4", "x = 6", "x = 8"],
                    "correct_answer": 1,
                    "explanation": "Subtract 5 from both sides: 2x = 8. Divide by 2: x = 4.",
                    "workings": "Step 1: Start with the equation\n2x + 5 = 13\n\nStep 2: Subtract 5 from both sides\n2x + 5 - 5 = 13 - 5\n2x = 8\n\nStep 3: Divide both sides by 2\n2x ÷ 2 = 8 ÷ 2\nx = 4\n\nStep 4: Check: 2(4) + 5 = 8 + 5 = 13 ✓\n\nAnswer: x = 4"
                },
                {
                    "question": "What is the square root of 144?",
                    "options": ["10", "11", "12", "13"],
                    "correct_answer": 2,
                    "explanation": "12 × 12 = 144, so √144 = 12.",
                    "workings": "Step 1: Find the number that multiplies by itself to give 144\n√144 = ?\n\nStep 2: Test values\n10 × 10 = 100 (too small)\n11 × 11 = 121 (too small)\n12 × 12 = 144 ✓\n13 × 13 = 169 (too large)\n\nStep 3: Verify\n12 × 12 = 144\n\nAnswer: √144 = 12"
                },
                {
                    "question": "If a triangle has sides 3, 4, and 5, what is its area?",
                    "options": ["6", "12", "15", "20"],
                    "correct_answer": 0,
                    "explanation": "This is a right triangle. Area = (base × height) / 2 = (3 × 4) / 2 = 6.",
                    "workings": "Step 1: Identify the triangle type\nSides are 3, 4, and 5\nSince 3² + 4² = 5² (9 + 16 = 25)\nThis is a right triangle\n\nStep 2: Identify base and height\nFor a right triangle, the two shorter sides are the base and height\nBase = 3\nHeight = 4\n\nStep 3: Apply area formula\nArea = (base × height) / 2\nArea = (3 × 4) / 2\nArea = 12 / 2\nArea = 6 square units\n\nAnswer: 6"
                },
                {
                    "question": "What percentage is 25 out of 50?",
                    "options": ["25%", "40%", "50%", "75%"],
                    "correct_answer": 2,
                    "explanation": "(25/50) × 100 = 50%.",
                    "workings": "Step 1: Write the fraction\nFraction = 25/50\n\nStep 2: Simplify the fraction\n25/50 = 1/2 = 0.5\n\nStep 3: Convert to percentage\n0.5 × 100 = 50%\n\nAlternative method:\nPercentage = (Part / Whole) × 100\n= (25 / 50) × 100\n= 0.5 × 100\n= 50%\n\nAnswer: 50%"
                },
                {
                    "question": "What is the value of 3² + 4²?",
                    "options": ["7", "12", "25", "49"],
                    "correct_answer": 2,
                    "explanation": "3² = 9 and 4² = 16. Adding them: 9 + 16 = 25.",
                    "workings": "Step 1: Calculate 3²\n3² = 3 × 3 = 9\n\nStep 2: Calculate 4²\n4² = 4 × 4 = 16\n\nStep 3: Add the squares\n9 + 16 = 25\n\nAnswer: 25"
                },
                {
                    "question": "Solve: 3x - 7 = 8",
                    "options": ["x = 5", "x = 1", "x = 3", "x = 15"],
                    "correct_answer": 0,
                    "explanation": "Add 7 to both sides: 3x = 15. Divide by 3: x = 5.",
                    "workings": "Step 1: Start with the equation\n3x - 7 = 8\n\nStep 2: Add 7 to both sides\n3x - 7 + 7 = 8 + 7\n3x = 15\n\nStep 3: Divide both sides by 3\nx = 15 ÷ 3\nx = 5\n\nStep 4: Check: 3(5) - 7 = 15 - 7 = 8 ✓\n\nAnswer: x = 5"
                },
                {
                    "question": "What is 25% of 80?",
                    "options": ["16", "20", "25", "40"],
                    "correct_answer": 1,
                    "explanation": "25% of 80 = (25/100) × 80 = 0.25 × 80 = 20.",
                    "workings": "Step 1: Convert percentage to decimal\n25% = 25/100 = 0.25\n\nStep 2: Multiply by the number\n0.25 × 80 = 20\n\nAlternative:\n25% = 1/4\n1/4 of 80 = 80 ÷ 4 = 20\n\nAnswer: 20"
                },
                {
                    "question": "What is the value of 2³?",
                    "options": ["6", "8", "9", "12"],
                    "correct_answer": 1,
                    "explanation": "2³ = 2 × 2 × 2 = 8.",
                    "workings": "Step 1: Understand exponent notation\n2³ means 2 to the power of 3\nThis means multiply 2 by itself 3 times\n\nStep 2: Calculate\n2³ = 2 × 2 × 2\n= 4 × 2\n= 8\n\nAnswer: 8"
                },
                {
                    "question": "Solve: x/4 = 5",
                    "options": ["x = 1", "x = 9", "x = 20", "x = 25"],
                    "correct_answer": 2,
                    "explanation": "Multiply both sides by 4: x = 5 × 4 = 20.",
                    "workings": "Step 1: Start with the equation\nx/4 = 5\n\nStep 2: Multiply both sides by 4\n(x/4) × 4 = 5 × 4\nx = 20\n\nStep 3: Check: 20/4 = 5 ✓\n\nAnswer: x = 20"
                },
                {
                    "question": "What is the circumference of a circle with radius 5?",
                    "options": ["10π", "25π", "5π", "15π"],
                    "correct_answer": 0,
                    "explanation": "Circumference = 2πr = 2π(5) = 10π.",
                    "workings": "Step 1: Recall the circumference formula\nC = 2πr\nwhere r is the radius\n\nStep 2: Substitute r = 5\nC = 2π(5)\nC = 10π\n\nAnswer: 10π (or approximately 31.4)"
                },
                {
                    "question": "What is 6 + 3 × 2?",
                    "options": ["18", "12", "9", "8"],
                    "correct_answer": 1,
                    "explanation": "Using order of operations (BODMAS/PEMDAS), multiplication comes before addition: 3 × 2 = 6, then 6 + 6 = 12.",
                    "workings": "Step 1: Remember order of operations (PEMDAS/BODMAS)\nBrackets/Parentheses\nOrders/Exponents\nDivision and Multiplication (left to right)\nAddition and Subtraction (left to right)\n\nStep 2: Apply to 6 + 3 × 2\nMultiply first: 3 × 2 = 6\nThen add: 6 + 6 = 12\n\nAnswer: 12\n\nNote: NOT (6+3) × 2, because multiplication is done first"
                },
                {
                    "question": "What is the area of a square with side length 7?",
                    "options": ["28", "49", "14", "56"],
                    "correct_answer": 1,
                    "explanation": "Area of a square = side × side = 7 × 7 = 49.",
                    "workings": "Step 1: Recall the area formula for a square\nArea = side × side = side²\n\nStep 2: Substitute side = 7\nArea = 7 × 7\nArea = 7²\nArea = 49 square units\n\nAnswer: 49"
                },
                {
                    "question": "What is 50 ÷ 5 × 2?",
                    "options": ["5", "20", "100", "50"],
                    "correct_answer": 1,
                    "explanation": "Using order of operations, division and multiplication are done left to right: 50 ÷ 5 = 10, then 10 × 2 = 20.",
                    "workings": "Step 1: Remember that division and multiplication have equal priority\nWhen they appear together, work left to right\n\nStep 2: Apply to 50 ÷ 5 × 2\nDivide first (left): 50 ÷ 5 = 10\nThen multiply: 10 × 2 = 20\n\nAnswer: 20\n\nNote: NOT 50 ÷ (5 × 2) = 50 ÷ 10 = 5"
                }
            ],
            "english": [
                {
                    "question": "What is a metaphor?",
                    "options": ["A comparison using 'like' or 'as'", "A direct comparison without using 'like' or 'as'", "Repetition of sounds", "Giving human qualities to non-human things"],
                    "correct_answer": 1,
                    "explanation": "A metaphor is a direct comparison. A simile uses 'like' or 'as'."
                },
                {
                    "question": "In 'Romeo and Juliet', what is the main conflict?",
                    "options": ["Two lovers from rival families", "A war between kingdoms", "A love triangle", "A curse on a family"],
                    "correct_answer": 0,
                    "explanation": "The central conflict is the forbidden love between Romeo and Juliet, whose families are feuding."
                },
                {
                    "question": "What does 'irony' mean?",
                    "options": ["Exaggeration", "Expressing something opposite to what is meant", "Repetition", "Silence"],
                    "correct_answer": 1,
                    "explanation": "Irony is when the opposite of what is expected occurs, or when someone says the opposite of what they mean."
                },
                {
                    "question": "Which literary device is this: 'The moon smiled down at the sleeping earth'?",
                    "options": ["Metaphor", "Personification", "Alliteration", "Simile"],
                    "correct_answer": 1,
                    "explanation": "Personification gives human qualities (smiling) to non-human things (the moon)."
                },
                {
                    "question": "What is the theme of a story?",
                    "options": ["The plot", "The main idea or message", "The setting", "The dialogue"],
                    "correct_answer": 1,
                    "explanation": "Theme is the underlying message or life lesson in a story."
                }
            ],
            "science": [
                {
                    "question": "What is photosynthesis?",
                    "options": ["Breaking down food for energy", "Converting sunlight into chemical energy", "Exchanging gases in the lungs", "Movement of water in plants"],
                    "correct_answer": 1,
                    "explanation": "Photosynthesis is the process where plants use sunlight to create glucose (sugar) from CO₂ and water."
                },
                {
                    "question": "What are the three states of matter?",
                    "options": ["Hot, cold, warm", "Solid, liquid, gas", "Element, compound, mixture", "Atom, molecule, ion"],
                    "correct_answer": 1,
                    "explanation": "The three states of matter are solid (fixed shape), liquid (takes shape of container), and gas (no fixed shape)."
                },
                {
                    "question": "Which organelle is the powerhouse of the cell?",
                    "options": ["Nucleus", "Chloroplast", "Mitochondria", "Ribosome"],
                    "correct_answer": 2,
                    "explanation": "Mitochondria are called the powerhouse because they produce ATP (energy) through cellular respiration."
                },
                {
                    "question": "What is the pH of a neutral solution?",
                    "options": ["0", "7", "14", "5"],
                    "correct_answer": 1,
                    "explanation": "pH 7 is neutral. Below 7 is acidic, above 7 is basic/alkaline."
                },
                {
                    "question": "What is the speed of light?",
                    "options": ["300,000 m/s", "150,000 m/s", "500,000 m/s", "1,000,000 m/s"],
                    "correct_answer": 0,
                    "explanation": "The speed of light is approximately 3 × 10⁸ m/s or 300,000 km/s."
                }
            ],
            "french": [
                {
                    "question": "Comment ça va?",
                    "options": ["How old are you?", "What is your name?", "How are you?", "Where are you from?"],
                    "correct_answer": 2,
                    "explanation": "'Comment ça va?' means 'How are you?' in French."
                },
                {
                    "question": "What does 'Je m'appelle' mean?",
                    "options": ["I like", "My name is", "I live", "I study"],
                    "correct_answer": 1,
                    "explanation": "'Je m'appelle' literally means 'I call myself', which is how you introduce your name in French."
                },
                {
                    "question": "Which is the correct plural of 'le chat'?",
                    "options": ["le chats", "les chats", "la chats", "chats"],
                    "correct_answer": 1,
                    "explanation": "The plural article is 'les' (for both masculine and feminine). So 'les chats' (the cats)."
                },
                {
                    "question": "What does 'au revoir' mean?",
                    "options": ["Good morning", "Goodbye", "Thank you", "Please"],
                    "correct_answer": 1,
                    "explanation": "'Au revoir' means 'goodbye' or literally 'until we see each other again'."
                },
                {
                    "question": "How do you say 'I eat an apple' in French?",
                    "options": ["Je mangez une pomme", "Je manger une pomme", "Je mange une pomme", "Je manges une pomme"],
                    "correct_answer": 2,
                    "explanation": "The correct conjugation of 'manger' (to eat) with 'je' is 'je mange'."
                }
            ],
            "finearts": [
                {
                    "question": "What is the primary color that is NOT a primary color in light?",
                    "options": ["Red", "Blue", "Yellow", "Green"],
                    "correct_answer": 2,
                    "explanation": "In light (RGB), the primary colors are Red, Green, and Blue. In pigment (RYB), they are Red, Yellow, and Blue."
                },
                {
                    "question": "What art movement is Pablo Picasso famous for?",
                    "options": ["Impressionism", "Cubism", "Surrealism", "Romanticism"],
                    "correct_answer": 1,
                    "explanation": "Picasso is one of the founders of Cubism, which broke down objects into geometric shapes."
                },
                {
                    "question": "What is perspective in art?",
                    "options": ["The artist's opinion", "Technique for creating depth and dimension", "Color harmony", "The subject matter"],
                    "correct_answer": 1,
                    "explanation": "Perspective is a technique that creates the illusion of depth on a 2D surface using lines and proportion."
                },
                {
                    "question": "Which color theory explains complementary colors?",
                    "options": ["Color harmony", "Color wheel", "Color psychology", "Color contrast"],
                    "correct_answer": 1,
                    "explanation": "The color wheel shows complementary colors (colors opposite each other) that create maximum contrast."
                },
                {
                    "question": "What is the golden ratio in art?",
                    "options": ["1:2", "1:1.618", "1:3", "2:1"],
                    "correct_answer": 1,
                    "explanation": "The golden ratio (approximately 1:1.618) is a proportion considered aesthetically pleasing and found in nature."
                }
            ]
        }

        questions = sample_quizzes.get(subject.lower(), [])
        if not questions:
            return []

        # Filter out already used questions
        available_questions = [q for q in questions if q.get("question") not in exclude_questions]

        # If we've used all questions, reset and start fresh
        if not available_questions:
            available_questions = questions

        # Randomly select requested number of questions from the pool
        # This ensures variety - different questions each time
        if len(available_questions) >= question_count:
            # Sample without replacement if we have enough questions
            return random.sample(available_questions, question_count)
        else:
            # If not enough unique questions, return all and repeat some
            selected = random.sample(available_questions, len(available_questions))
            remaining = question_count - len(available_questions)
            selected.extend(random.choices(available_questions, k=remaining))
            return selected

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
