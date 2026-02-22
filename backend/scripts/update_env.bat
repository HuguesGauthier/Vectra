@echo off
echo [INFO] Updating local virtual environment...
if not exist "venv" (
    echo [ERROR] Virtual environment 'venv' not found. Please create it first.
    exit /b 1
)
".\venv\Scripts\python.exe" -m pip install --upgrade pip
".\venv\Scripts\python.exe" -m pip install -r requirements.txt
echo [SUCCESS] Environment updated.
pause
