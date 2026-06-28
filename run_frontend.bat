@echo off
setlocal enabledelayedexpansion

REM Use the full path to the venv Python
set PYTHON_EXE=%CD%\mytutor\Scripts\python.exe

REM Set environment variables
set PYTHONPATH=%CD%
set FASTAPI_URL=http://127.0.0.1:8000
if not defined ANTHROPIC_API_KEY (
  echo Warning: ANTHROPIC_API_KEY not set
)

REM Run streamlit using the venv Python directly
%PYTHON_EXE% -m streamlit run src/frontend/chatbot_streamlit.py --server.port 8501 --logger.level=error --client.showErrorDetails=false
