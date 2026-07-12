"""
Agent Orchestrator - Routes requests to specialized agents.
Uses ReAct agents for tutoring and quiz generation.
"""

import logging
from langchain_core.messages import HumanMessage
from src.agents.chat_tutor_agent import create_chat_tutor_agent
from src.agents.quiz_agent import create_quiz_agent

logger = logging.getLogger(__name__)

# Intent detection keywords for routing
QUIZ_KEYWORDS = [
    "quiz", "quizzes", "create a quiz", "generate a quiz", "give me a quiz",
    "test me", "practice questions", "exam practice", "question bank",
    "make a quiz", "build a quiz"
]

TUTORING_KEYWORDS = [
    "what is", "explain", "how do", "help me", "answer", "define",
    "teach me", "tell me about", "describe", "clarify", "understand"
]


def detect_intent(query: str) -> str:
    """
    Detect whether a query is a quiz request or a tutoring question.

    Args:
        query: User's input query

    Returns:
        "quiz" or "tutoring" based on detected intent
    """
    query_lower = query.lower()

    # Check for quiz keywords first (more specific)
    for keyword in QUIZ_KEYWORDS:
        if keyword in query_lower:
            logger.info(f"Detected quiz intent: {query[:50]}")
            return "quiz"

    # Check for tutoring keywords
    for keyword in TUTORING_KEYWORDS:
        if keyword in query_lower:
            logger.info(f"Detected tutoring intent: {query[:50]}")
            return "tutoring"

    # Default to tutoring for most educational questions
    logger.info(f"Defaulting to tutoring intent: {query[:50]}")
    return "tutoring"


def route_query(query: str):
    """
    Route a query to the appropriate specialized agent.

    Args:
        query: User's input query

    Returns:
        Response from the appropriate agent
    """
    intent = detect_intent(query)

    if intent == "quiz":
        logger.info("Routing to Quiz Agent")
        agent = create_quiz_agent()
    else:
        logger.info("Routing to Chat Tutor Agent")
        agent = create_chat_tutor_agent()

    # Invoke the agent with the query
    response = agent.invoke({"messages": [HumanMessage(content=query)]})
    return response


def create_agent():
    """
    Legacy function for backward compatibility.
    Creates a chat tutor agent (the default agent for most operations).

    Returns:
        Configured chat tutor agent
    """
    logger.info("Using legacy create_agent() - returning Chat Tutor Agent")
    return create_chat_tutor_agent()
