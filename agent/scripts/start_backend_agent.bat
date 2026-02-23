@echo off
chcp 65001 >NUL
cd /d "%~dp0"

echo [INFO] Activating Virtual Environment...
set VENV_PYTHON=%~dp0..\..\backend\.venv\Scripts\python.exe

if not exist "%VENV_PYTHON%" (
    echo [ERROR] Virtual environment python not found at %VENV_PYTHON%
    echo Please ensure .venv exists in backend/ directory.
    pause
    exit /b 1
)

echo [INFO] Switching context to backend...
echo [INFO] Switching context to backend...
cd ..\..\backend

echo [INFO] Installing Agent dependencies...
"%VENV_PYTHON%" -m pip install -q gitpython google-generativeai python-dotenv mcp black isort flake8

echo [INFO] Running Nightly Agentic Worker...
"%VENV_PYTHON%" ..\agent\src\runners\backend_agent_runner.py %*

echo [DONE] Agent Session Finished.
pause
