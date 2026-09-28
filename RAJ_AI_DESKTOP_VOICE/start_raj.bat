@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title RAJ AI Launcher

where py >nul 2>&1
if %errorlevel%==0 (
    set "PYTHON=py -3"
) else (
    where python >nul 2>&1
    if errorlevel 1 (
        echo Python 3 was not found. Install Python 3 and try again.
        pause
        exit /b 1
    )
    set "PYTHON=python"
)

if not exist ".venv\Scripts\python.exe" (
    echo Creating RAJ virtual environment...
    %PYTHON% -m venv .venv
    if errorlevel 1 (
        echo Could not create the virtual environment.
        pause
        exit /b 1
    )
)

echo Checking RAJ requirements...
".venv\Scripts\python.exe" -m pip install -r backend\requirements.txt
if errorlevel 1 (
    echo.
    echo Requirements installation failed.
    pause
    exit /b 1
)

start "RAJ Backend + Always Voice" cmd /k "cd /d ""%~dp0backend"" && ""%~dp0.venv\Scripts\python.exe"" app.py"
timeout /t 3 /nobreak >nul
start "RAJ Frontend" cmd /k "cd /d ""%~dp0"" && ""%~dp0.venv\Scripts\python.exe"" -m http.server 5173 --directory frontend"
timeout /t 2 /nobreak >nul
start "" "http://127.0.0.1:5173/?always=1"

echo.
echo ===============================================
echo RAJ AI is running in ALWAYS LISTENING mode.
echo Say: "Raj open Chrome"
echo Say: "Raj open YouTube"
echo Say: "Raj take a screenshot"
echo ===============================================
echo.
endlocal
