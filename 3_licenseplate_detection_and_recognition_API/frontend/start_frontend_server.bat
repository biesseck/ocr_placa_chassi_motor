@echo off
setlocal EnableExtensions

REM Move to the directory where this .bat file is located
cd /d "%~dp0"

npm run dev -- --host 0.0.0.0

pause
endlocal