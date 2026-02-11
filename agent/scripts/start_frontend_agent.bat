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

echo [INFO] Running Frontend Refactor Agent...
echo [TIP] Usage: start_frontend_agent.bat frontend/src/components/MyComponent.vue --goal "Refactor it"
"%VENV_PYTHON%" ..\src\runners\frontend_agent_runner.py %*

echo [DONE] Agent Session Finished.
pause
