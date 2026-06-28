param(
    [int]$Port = 8000
)

# Activate the virtual environment
& ".\mytutor\Scripts\Activate.ps1"

# Set Python path
$env:PYTHONPATH = "$PWD"
$env:ANTHROPIC_API_KEY = $env:ANTHROPIC_API_KEY  # Make sure it's available

# Run uvicorn
python -m uvicorn src.main:app --host 127.0.0.1 --port $Port --log-level info
