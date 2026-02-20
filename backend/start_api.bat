@echo off




REM Force Python to flush stdout/stderr immediately
set PYTHONUNBUFFERED=1

".\venv\Scripts\uvicorn.exe" app.main:app --reload
pause
