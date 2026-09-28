@echo off
setlocal
set "LINK=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\RAJ AI.lnk"
if exist "%LINK%" del /f /q "%LINK%"
echo RAJ AI startup has been disabled.
pause
