@echo off
setlocal
title Stop RAJ AI
echo Stopping RAJ services on local ports 5000 and 5173...

for /f "tokens=5" %%P in ('netstat -ano ^| findstr ":5000" ^| findstr "LISTENING"') do taskkill /PID %%P /F >nul 2>&1
for /f "tokens=5" %%P in ('netstat -ano ^| findstr ":5173" ^| findstr "LISTENING"') do taskkill /PID %%P /F >nul 2>&1

echo RAJ AI has been stopped.
endlocal