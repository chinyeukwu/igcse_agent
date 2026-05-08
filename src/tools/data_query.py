import hashlib
import logging
from click import prompt
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from pydantic import SecretStr
import pandas as pd
import src.config as config
from pathlib import Path
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

# Singleton LLM instance
_llm_instance = None

# Simple in-memory cache for LLM responses
_llm_cache = {}

@tool
def query_data(query: str) -> str | None:
    """Query football match data from a CSV file using LLM.
    Args:
        query (str): The natural language query to ask about the football match data.
    
    Returns:
        str: The response from the LLM based on the query.
    """

    # Load your CSV file
    file_path = Path(config.file_path)
    data = load_csv(file_path)
    
    if data is not None:
        # Ask a natural language question
        user_query = query
        result = analyze_csv_with_llm(data, user_query)

        if result:
            logger.debug("LLM Response:")
            logger.debug(result)
            return result
        else:
            logger.warning("No response from LLM.")
            return "No response from LLM."
    else:
        logger.error("Failed to load data.")
        return "Failed to load data." 



def load_csv(file_path) -> pd.DataFrame | None:
    """Load the CSV file into a pandas DataFrame."""
    try:
        data = pd.read_csv(file_path)
        return data
    except Exception as e:
        logger.error(f"Error loading CSV: {e}")
        return None

def create_llm() -> ChatOpenAI | None:
    """Get or create the singleton ChatOpenAI instance."""
    global _llm_instance
    try:
        if _llm_instance is not None:
            return _llm_instance

        if config.openai_key is None:
            raise ValueError("OPENAI_API_KEY environment variable is not set.")

        _llm_instance = ChatOpenAI(
            model="gpt-4",
            temperature=0,
            api_key=SecretStr(config.openai_key),
            timeout=30,
            max_retries=2,
        )
        return _llm_instance
    except Exception as e:
        logger.error(f"Error creating LLM: {e}")
        return None

def query_llm(prompt) -> dict:
    """Send a natural language query to the LLM and get a response."""
    try:
        # Check cache first
        cache_key = hashlib.sha256(prompt.encode()).hexdigest()
        if cache_key in _llm_cache:
            logger.debug(f"Cache hit for prompt hash {cache_key}")
            return _llm_cache[cache_key]

        chatllm = create_llm()
        if chatllm is None:
            logger.error("LLM creation failed.")
            return {"error": "LLM creation failed."}
        # Get the response from the LLM
        response = chatllm.invoke([HumanMessage(content=prompt)])
        logger.debug(response.content)
        result = {"llmresponse": str(response.content)}

        # Cache the response
        _llm_cache[cache_key] = result
        logger.debug(f"Cached response for prompt hash {cache_key}")

        return result
    except Exception as e:
        logger.error(f"Error querying LLM: {e}")
        return ""

def analyze_csv_with_llm(data, query) -> str | None:
    """Generate a prompt for the LLM to analyze the CSV data."""
    # Convert the DataFrame to a string
    data_preview = data.head(10).to_string(index=False)
    prompt = (
        f"""You are an AI assistant specialized in analyzing football match data.
        The dataset contains historical football match data, including teams, scores, and other relevant statistics.    
        Here is a preview of the data:\n\n{data_preview}\n\n
        Your task is to analyze this data and provide insights based on the user's query.
        The user has asked:\n\n{query}\n\n
        Please provide a detailed response based on the data provided.
        The response should be concise and directly address the user's query.
        The response should be in natural language and easy to understand.
        If the query is not answerable with the provided data, please state that clearly.
        If the query is ambiguous, ask for clarification.
        If the query requires specific data points, ensure to reference them in your response.
        If the query involves calculations, provide the calculations and the final result.
        If the query involves comparisons, provide the comparisons and the final result.
        If the query involves trends, provide the trends using charts or graphs and the final result.
        If the query involves statistics, provide the statistics and the final result.
        The response should in a structured format, listing key points in bullet points and returned as a dictionary in JSON format.

        Example query: "What is the average score of matches played by Manchester United in the 2020 season?"
        Example response:
        {{
            "answer": 2.5,
            "details": "Manchester United played 38 matches in the 2020 season with an average score of 2.5 goals per match."
        }}

        Example query: "What is the average number of goals scored by Arsenal in the 2018 season?"
        Example response:
        {{
            "answer": 2.0,
            "details": "Arsenal played 38 matches in the 2018 season with an average score of 2.0 goals per match."
        }}
       """
    )
    return query_llm(prompt)

# function to load csv file into pandas dataframe
def load_csv_to_dataframe(file_path: str) -> pd.DataFrame:
    try:
        df = pd.read_csv(file_path)
        return df
    except Exception as e:
        logger.error(f"Error loading CSV: {e}")
        return pd.DataFrame()