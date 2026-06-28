@echo off
setlocal enabledelayedexpansion

REM Use the full path to the venv Python
set PYTHON_EXE=%CD%\mytutor\Scripts\python.exe

REM Set environment variables
set PYTHONPATH=%CD%
if not defined ANTHROPIC_API_KEY (
  echo Warning: ANTHROPIC_API_KEY not set
)
set FASTAPI_URL=http://127.0.0.1:8000
set FASTAPI_PORT=8000

REM Run uvicorn using the venv Python directly
%PYTHON_EXE% -m uvicorn src.main:app --host 127.0.0.1 --port 8000 --log-level info
