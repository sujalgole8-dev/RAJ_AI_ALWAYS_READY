@echo off
setlocal
title RAJ AI Backend
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Run start_raj.bat once first so the virtual environment is created.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -m pip install -r backend\requirements.txt
cd backend
".\..\.venv\Scripts\python.exe" app.py
endlocal