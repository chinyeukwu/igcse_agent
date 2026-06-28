param(
    [int]$Port = 8501
)

# Activate the virtual environment
& ".\mytutor\Scripts\Activate.ps1"

# Set Python path and API key
$env:PYTHONPATH = "$PWD"
$env:ANTHROPIC_API_KEY = $env:ANTHROPIC_API_KEY  # Make sure it's available
$env:FASTAPI_URL = "http://127.0.0.1:8000"

# Run streamlit
python -m streamlit run src/frontend/chatbot_streamlit.py --server.port $Port --logger.level=error
