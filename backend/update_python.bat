@echo off
".\.venv\Scripts\python.exe" -m pip install --upgrade pip setuptools wheel
".\.venv\Scripts\python.exe" -m pip install -r requirements.txt
pause
