@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo RAJ is not installed yet. Run start_raj.bat first.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" backend\voice_test.py
endlocal
