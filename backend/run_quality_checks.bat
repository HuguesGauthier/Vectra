@echo off
REM Script to run Black, Isort, and Flake8 on the backend project
REM Outputs reports to the 'quality_reports' directory

echo ========================================================
echo      Vectra Backend - Code Quality Automation
echo ========================================================

REM Create reports directory if it doesn't exist
if not exist "quality_reports" mkdir "quality_reports"

echo.
echo [1/3] Running Black (Code Formatter)...
echo ---------------------------------------
.\.venv\Scripts\black . > quality_reports\black_output.txt 2>&1
echo Logs saved to quality_reports\black_output.txt

echo.
echo [2/3] Running Isort (Import Sorter)...
echo --------------------------------------
.\.venv\Scripts\isort . > quality_reports\isort_output.txt 2>&1
echo Logs saved to quality_reports\isort_output.txt

echo.
echo [3/3] Running Flake8 (Linter)...
echo --------------------------------
REM --exit-zero ensures the script continues even if errors are found
.\.venv\Scripts\flake8 . --output-file=quality_reports\flake8_report.txt --exit-zero
echo Report saved to quality_reports\flake8_report.txt

echo.
echo ========================================================
echo Execution Complete!
echo You can find the detailed reports in the 'quality_reports' folder.
echo ========================================================
pause
