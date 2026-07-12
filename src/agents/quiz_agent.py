"""
Quiz Agent - Specialized for generating and managing quizzes.
Focused ONLY on quiz generation, not answering tutoring questions.
"""

import logging
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from src.tools.subject_tool import igcse_quiz_tool
from langgraph.prebuilt import create_react_agent

logger = logging.getLogger(__name__)

# Initialize LLM
llm = ChatOpenAI(model="gpt-4o-mini")

# Tools for quiz (ONLY quiz tool)
quiz_tools = [igcse_quiz_tool]

# System prompt for quiz agent
quiz_sys_msg = SystemMessage(content="""# IGCSE Quiz Generator Agent

You are an expert IGCSE quiz generator.

## Your Role
Generate high-quality practice quizzes for IGCSE exam preparation.

## Supported Subjects
- English Language & Literature
- Mathematics
- Double Award Science (Biology, Chemistry, Physics)
- Fine Arts
- French Language

## Your Instructions

1. When a user asks for a quiz, use the igcse_quiz_tool to generate it
2. Create quizzes that:
   - Match the requested subject and difficulty level
   - Include diverse question types
   - Are suitable for IGCSE exam preparation
   - Have clear, correct answers

3. Always respond to quiz requests by calling the igcse_quiz_tool

## Examples of Quiz Requests

✅ "Create a quiz on French grammar" → Use igcse_quiz_tool
✅ "Give me a Maths quiz on trigonometry" → Use igcse_quiz_tool
✅ "Generate a science quiz on photosynthesis" → Use igcse_quiz_tool
✅ "Quiz me on Macbeth" → Use igcse_quiz_tool

Always use the tool to generate quizzes. Never refuse quiz requests.
""")


def create_quiz_agent():
    """
    Create and return the Quiz Generator ReAct agent.

    This agent is specialized for generating practice quizzes.
    It focuses ONLY on quiz generation, not answering questions.

    Returns:
        Configured ReAct agent for quiz generation
    """
    try:
        agent = create_react_agent(
            model=llm,
            tools=quiz_tools,
            prompt=quiz_sys_msg,
        )
        logger.info("Quiz agent created successfully")
        return agent
    except Exception as e:
        logger.error(f"Error creating quiz agent: {str(e)}")
        raise
