@echo off




REM Force Python to flush stdout/stderr immediately
set PYTHONUNBUFFERED=1

".\venv\Scripts\python.exe" -m uvicorn app.main:app --reload
pause
