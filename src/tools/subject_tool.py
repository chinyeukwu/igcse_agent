# this tool will help with French language tasks

import logging
from src.tools.data_query import query_llm
from langchain_core.tools import tool
import json
import re

logger = logging.getLogger(__name__)

# Pre-compiled regex patterns for JSON response parsing
UNESCAPED_QUOTE_PATTERN = re.compile(r'(\w)"(\w)')
DOUBLE_QUOTE_PATTERN = re.compile(r'"\s*\[?\s*""([^"]+)"')

@tool("answer_french_question_tool", description="Tool used to answer Edexcel IGCSE French Questions")
def answer_french_question_tool(question: str) -> dict:
    """
    Answer a user query regarding the Edexcel IGCSE curriculum in French using an LLM.
    The user query could be about any topic related to the French curriculum such as Grammar, Vocabulary, or Literature.

    Args:
        question (str): The question to answer in French.
        
    Returns:
        dict: The answer to the question in French.
    """
    # Create a prompt for the LLM to answer the question in French
    logger.debug("Asking LLM for answer in French...")

    prompt = f"""You are a French language tutor, who is an expert in the Edexcel IGCSE curriculum.
    Your task is to respond to a user's query or question in French:
    
    User's query: {question}\n\n

    ### start of instructions
    1. Use a professional tone to respond to the user's query.
    2. Provide a clear and concise answer in French, suitable for a student preparing for the Edexcel IGCSE exam.
    3. If the user's query is ambiguous, ask for clarification.
    4. The answer should be structured as follows in a valid json format:
       - Provide key points or explanations in a logical order.
       - Conclude with reasoning and an explanation for your response in English.
    5. Do NOT put any double or single quotes around strings or names of books, authors, or any other entities in the key points or explanations.
    ### end of instructions
     ---
    ### start of examples
    Example question: "What are the key themes in French literature?
    Example answer: 
    {{
        "answer" : {{
            "key_points":  ["Les thèmes clés de la littérature française incluent l'amour, la guerre, la société et la condition humaine. Des auteurs comme Victor Hugo et Gustave Flaubert ont exploré ces thèmes dans leurs œuvres."],
            "conclusion": "In conclusion, French literature offers a rich exploration of universal themes that continue to resonate with readers today."
        }}  
    }}

    Example question: "How do you conjugate regular -er verbs in the present tense?"
    Example answer: 
    {{
        "answer" : {{            
            "key_points":  ["Pour conjuguer les verbes réguliers en -er au présent, on enlève la terminaison -er et on ajoute les terminaisons appropriées : -e, -es, -e, -ons, -ez, -ent. Par exemple, pour le verbe 'parler', on dit 'je parle', 'tu parles', 'il/elle parle', 'nous parlons', 'vous parlez', 'ils/elles parlent'."],
            "conclusion": "In conclusion, mastering the conjugation of regular -er verbs is essential for effective communication in French."
        }}
    }}


    ### end of examples
    """
    # Call the LLM with the prompt
    logger.debug("Asking LLM for answer in French...")
    response = query_llm(prompt)
    logger.debug(f"LLM response from French tool: {response}")
    formatted_response = format_response(response.get("llmresponse", {}))
    return formatted_response

@tool("answer_igcse_questions_tool", description="Tool used to answer Edexcel IGCSE Maths, English, Double Award Science, Fine Arts and English Literature Questions")
def answer_igcse_questions_tool(question: str) -> dict:
    """
    Answer a user query regarding the Edexcel IGCSE curriculum in Maths, English, Double Award Science, Fine Arts and English Literature using an LLM.
    The user query could be about any topic related to the Edexcel IGCSE Maths, English, Double Award Science, Fine Arts and English Literature curriculum.

    Args:
        question (str): The Maths, English, Double Award Science, Fine Arts and English Literature question to answer.
        
    Returns:
        dict: The answer to the question in Maths, English, Double Award Science, Fine Arts and English Literature.
    """
    # Create a prompt for the LLM to answer the question in Maths, English, Double Award Science, Fine Arts and English Literature
    logger.debug("Asking LLM for answer in IGCSE subjects...")

    prompt = f"""You are a Maths, English, Double Award Science, Fine Arts and English Literature tutor, who is an expert in the Edexcel IGCSE curriculum.
    Your task is to answer a user's query or question in Maths, English, Double Award Science, Fine Arts and English Literature:

    User's query: {question}\n\n

    ### start of instructions
    1. Use a professional tone to respond to the user's query.
    2. Provide a clear and concise answer, suitable for a student preparing for the Edexcel IGCSE exam.
    3. If the user's query is ambiguous, ask for clarification.
    4. The answer MUST be in English and structured as follows in a valid json format:
       - Provide key points or explanations in a logical order.
       - Conclude with reasoning and an explanation for your response.
    5. Do NOT put any double or single quotes around strings or names of books, authors, or any other entities in the key points or explanations.
    ### end of instructions

    ---

    ### start of examples
    Example question: "What is the Pythagorean theorem and provide an example formula?"
    Example answer: 
    {{
        "answer" :{{
        "key_points": [
            "In a right triangle, the Pythagorean theorem relates the lengths of the sides.",
            "The formula is a² + b² = c², where c is the hypotenuse."
        ],
        "conclusion": "This theorem is fundamental in geometry and is used to find the length of a side in a right triangle."
        }}
    }}
    
    Example question: "How do you calculate the area of a circle?"
    Example answer: 
    {{ 
        "answer" :{{
        "key_points": [
            "The area of a circle is calculated using the formula A = πr², where r is the radius.",
            "To find the area, square the radius and multiply by π (approximately 3.14)."
        ],
        "conclusion": "This formula is essential for solving problems related to circles in geometry."
        }}
    }}

    Example question: "Give a summary of the Macbeth literature book"
    Example answer: 
    {{
        "answer" :{{
        "key_points": [
            "Macbeth is a tragedy by William Shakespeare.",
            "The story follows a Scottish general who is led to wicked thoughts by the prophecies of three witches.",
            "Driven by ambition and spurred on by his wife, he murders King Duncan and takes the throne.",
            "His reign is plagued by guilt and paranoia, leading to further violence and ultimately his downfall."
        ],
        "conclusion": "The play explores themes of ambition, power, guilt, and the supernatural."
        }}
    }}

    Example question: "What are key requirements for creative writing?"
    Example answer: 
    {{
        "answer" :{{
        "key_points": [
            "Creativity and originality are essential for producing unique written work.",
            "A strong command of language, including vocabulary and grammar, is crucial.",
            "Understanding narrative structure and character development enhances storytelling.",
            "Writers should be open to feedback and willing to revise their work."
        ],
        "conclusion": "These requirements help writers craft compelling and imaginative pieces.
        }}
    }}

    Example question: "What is photosynthesis?"
    Example answer: 
    {{
        "answer" :{{
        "key_points": [
            "Photosynthesis is the process by which green plants and some other organisms use sunlight to synthesize foods with the help of chlorophyll.",
            "It converts carbon dioxide and water into glucose and oxygen, using light energy."
        ],
        "conclusion": "This process is essential for life on Earth, as it provides the primary source of energy for nearly all organisms."
        }}
    }}

    Example question: "What are the key stages of cellular respiration?"
    Example answer: 
    {{
        "answer" :{{
        "key_points": [
            "Cellular respiration consists of three main stages: glycolysis, the Krebs cycle, and oxidative phosphorylation.",
            "Glycolysis occurs in the cytoplasm and breaks down glucose into pyruvate, producing a small amount of ATP.",
            "The Krebs cycle takes place in the mitochondria and processes pyruvate to produce electron carriers (NADH and FADH2).",
            "Oxidative phosphorylation occurs in the inner mitochondrial membrane, where ATP is produced using the electron transport chain."
        ],
        "conclusion": "These stages are crucial for converting glucose into usable energy (ATP) in cells."
        }}
    }}

    Example question: "What is the difference between an element and a compound?"
    Example answer: 
    {{
        "answer" :{{
        "key_points": [
            "An element is a pure substance that cannot be broken down into simpler substances by chemical means.",
            "A compound is a substance formed when two or more elements chemically combine in fixed proportions."
        ],
        "conclusion": "Understanding the distinction between elements and compounds is fundamental in chemistry."
    }}

    Example question: "What are some common techniques used in painting?"
    Example answer: 
    {{
        "answer" :{{
        "key_points": [
            "Common techniques used in painting include brushwork, glazing, impasto, and scumbling.",
            "Each technique can create different textures and effects in the artwork."
        ],
        "conclusion": "These techniques are essential for artists to express their creativity and achieve desired visual outcomes."
        }}  
    }}

    Example question: "Who are some influential artists of the 20th century?"
    Example answer: 
    {{
        "answer" :{{
        "key_points": [
            "Influential artists of the 20th century include Pablo Picasso, Vincent van Gogh, Frida Kahlo, and Jackson Pollock.",
            "Their works have had a significant impact on modern art."
        ],
        "conclusion": "These artists are celebrated for their unique styles and contributions to the art world."
        }}
    }}

    ### end of examples
    """
    
    # Call the LLM with the prompt
    logger.debug("Asking LLM for IGCSE subjects response...")
    response = query_llm(prompt)
    logger.debug(f"LLM response from IGCSE tool: {response}")
    formatted_response = format_response(response.get("llmresponse", {}))
    return formatted_response


@tool("igcse_quiz_tool", description="Tool used to generate quizzes or questions and answers for Edexcel IGCSE subjects")
def igcse_quiz_tool(question: str) -> dict:
    """
    Generate quiz questions and answers list for Edexcel IGCSE subjects based on the intent of the user's enquiry.
    Analyze the user's enquiry, understand what subject and topic the user wants a quiz for, and generate a list of 10 questions and answers.

    Args:
        question (str): The question to generate a quiz for.

    Returns:
        dict: A dictionary containing the quiz's list of questions and answers.
    """

    logger.debug("Generating quiz for Edexcel IGCSE subjects...")

    prompt = f"""You are a helpful assistant that is an expert examiner for Edexcel IGCSE subjects such as
    English Language, English Literature, Mathematics, Fine Arts, French and Double Award science.
    Your task is to create a quiz of 10 questions and answers based on the user's query.
    
    User's query: {question}\n\n

    ### start of instructions
    1. Analyse the user's query.
    2. Create a quiz of 10 questions and answers based on the user's query.
    3. For French language questions, the questions and answers should be in French.
    4. For English Language, English Literature, Mathematics, Fine Arts and Double Award science questions, the questions and answers must be in English.
    5. The response should be a valid json comprising a list of the quiz's questions followed by their answers.
    ### end of instructions
     ---
    ### start of examples
    Example question: Give me a quiz on the Macbeth book
    Example response: {{
        "quiz" : {{
            "questions": ["Who is the main protagonist in Macbeth?", "What happened to Macbeth?", "Who is the author of Macbeth?", "What is the name of Macbeth's wife", "Did Macbeth have any children?", "How did Macbeth die?", "Did Macbeth have any close friends?", "How old was Macbeth when he became king?", "Where was Macbeth from?", "Did Macbeth have any siblings?"],
            "answers": ["Macbeth", "He became mentally unstable", "William Shakespeare", "Dont know", "Yes", "Was poisoned", "Yes", "30 years Old", "UK", "Yes"]
        }}
    }}

    Example question: Give me a quiz on the French Revolution
    Example response: {{
        "quiz" : {{
            "questions": ["What year did the French Revolution begin?", "Who was the king of France during the revolution?", "What was the main cause of the French Revolution?", "What is the Declaration of the Rights of Man and of the Citizen?", "Who was Maximilien Robespierre?", "What was the Reign of Terror?", "What was the outcome of the French Revolution?", "How did the French Revolution impact the rest of Europe?", "What role did women play in the French Revolution?", "What is the legacy of the French Revolution?"],
            "answers": ["1789", "Louis XVI", "Social inequality and financial crisis", "A fundamental document of the revolution", "A leading figure during the revolution", "A period of extreme violence", "The rise of Napoleon Bonaparte", "It inspired other revolutions", "They were active participants", "It established the principles of liberty and equality"]
        }}
    }}

    ### end of examples
    """

    logger.debug(f"Quiz tool prompt: {prompt}")
    # Call the LLM with the prompt
    logger.debug("Asking LLM for response in Quiz tool...")
    response = query_llm(prompt)
    logger.debug(f"LLM response from quiz tool: {response}")
    formatted_response = format_response(response.get("llmresponse", {}))
    return formatted_response

def format_response(response: dict) -> dict:
    """
    Extract the AI message from the response dictionary.

    Args:
        response (dict): The response dictionary from the LLM.

    Returns:
        dict: The extracted AI message.
    """

    logger.debug(f"Raw response: {response}")
    cleaned_response = str(response).replace("\n", "").replace("'", '"').strip()
    # Fix unescaped double quotes inside values (e.g., Eva"s -> Eva's)
    cleaned_response = UNESCAPED_QUOTE_PATTERN.sub(r"\1'\2", cleaned_response)
    # Fix double double-quotes at the start of string values: ""Text" -> "Text
    cleaned_response = DOUBLE_QUOTE_PATTERN.sub(r'"[\1"', cleaned_response)
    logger.debug(f"Cleaned response: {cleaned_response}")

    try:
        jsonresponse = json.loads(cleaned_response)
        logger.debug(f"JSON response: {jsonresponse}")
        if "quiz" in jsonresponse and isinstance(jsonresponse["quiz"], dict):
            questions = jsonresponse["quiz"].get("questions", [])
            answers = jsonresponse["quiz"].get("answers", [])
            if isinstance(questions, str):
                questions = [questions]
            if isinstance(answers, str):
                answers = [answers]
            logger.debug(f"Questions: {questions}\nAnswers: {answers}")
            return {"questions": questions, "answers": answers}
        if "answer" in jsonresponse and isinstance(jsonresponse["answer"], dict):
            key_points = jsonresponse["answer"].get("key_points", [])
            conclusion = jsonresponse["answer"].get("conclusion", "")
            if isinstance(key_points, str):
                key_points = list(key_points)
            if conclusion and isinstance(conclusion, str):
                conclusion = [conclusion]
            logger.debug(f"Key Points: {key_points}\nConclusion: {conclusion}")
            return {"Key Points": key_points, "Conclusion": conclusion}
        return {}
    except Exception as e:
        logger.error(f"Error parsing response: {e}")
        return {}