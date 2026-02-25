@echo off
cd /d "%~dp0"

set "VENV_PYTHON=..\backend\.venv\Scripts\python.exe"

if not exist "%VENV_PYTHON%" (
    echo [ERROR] Virtual environment not found at %VENV_PYTHON%
    echo Please ensure the venv exists in backend/.venv
    pause
    exit /b 1
)

echo [INFO] Launching MkDocs Server on http://localhost:8002/Vectra/
"%VENV_PYTHON%" -m mkdocs serve -a localhost:8002
pause
