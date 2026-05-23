@echo off
setlocal EnableExtensions

REM Move to the directory where this .bat file is located
cd /d "%~dp0"

set "CONDA_ENV=licenseplate_ocr_api_py310"
set "USE_CONDA="s

REM Check if Conda is available
where conda >nul 2>&1 && set "USE_CONDA=1"

REM Try to activate env (only if init worked)
if defined USE_CONDA (
    echo Activating conda env: %CONDA_ENV%
    call conda activate "%CONDA_ENV%" >nul 2>&1
    echo %cd%
    echo Starting API Server...
    call uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
) else (
    echo ERROR: Anaconda not available. Install it first.
    pause
    exit /b 1
)

pause
endlocal