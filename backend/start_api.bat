@echo off

:: Load ENABLE_PHOENIX_TRACING from .env if present
if exist "..\.env" (
    for /f "usebackq tokens=1* delims==" %%A in ("..\.env") do (
        if /i "%%A"=="ENABLE_PHOENIX_TRACING" (
            echo [Startup] Found Phoenix config in .env: %%B
            set "ENABLE_PHOENIX_TRACING=%%B"
        )
    )
)


REM Force Python to flush stdout/stderr immediately
set PYTHONUNBUFFERED=1

".\.venv\Scripts\uvicorn.exe" app.main:app --reload
pause
