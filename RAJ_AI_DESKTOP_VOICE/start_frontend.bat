@echo off
setlocal
title RAJ AI Frontend
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    set "PYTHON=.venv\Scripts\python.exe"
) else (
    set "PYTHON=python"
)

start "" "http://127.0.0.1:5173"
%PYTHON% -m http.server 5173 --directory frontend
endlocal