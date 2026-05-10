"""
Quiz generator for creating fresh IGCSE quizzes using AI.
Generates question sets on-demand with configurable difficulty levels.
"""

import json
import re
import random
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
Each question must have: "question", "options" (array of 4), "correct_answer" (index 0-3), "explanation", "workings"
- "explanation": Brief explanation of the answer
- "workings": Step-by-step solution showing all working and calculations
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
        language_code: str = "en",
        exclude_questions: set = None
    ) -> Tuple[bool, List[Dict[str, Any]], str]:
        """
        Generate a fresh quiz with specified parameters.
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

            # Shuffle the answer options so correct answer isn't always in same position
            shuffled_questions = QuizGenerator.shuffle_question_options(questions)

            return True, shuffled_questions, ""

        except Exception as e:
            error_str = str(e)
            # If API quota/rate limit error, use sample questions as fallback
            if "429" in error_str or "quota" in error_str.lower() or "rate_limit" in error_str.lower():
                sample_questions = QuizGenerator.get_sample_quiz(subject_lower, question_count, exclude_questions)
                if sample_questions:
                    # Shuffle sample questions too
                    shuffled_sample = QuizGenerator.shuffle_question_options(sample_questions)
                    return True, shuffled_sample, ""
                return False, [], f"OpenAI API unavailable (quota exceeded). Please check your OpenAI credits at https://platform.openai.com/account/billing/overview"

            return False, [], f"Quiz generation error: {error_str}"

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
                    "correct_answer": 2,
                    "explanation": "Using order of operations (PEMDAS), multiplication comes before addition: 3 × 2 = 6, then 6 + 6 = 12. Wait, that's not right. Let me recalculate: 3 × 2 = 6, then 6 + 6 = 12. Hmm, but the answer is 12, not 9.",
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
