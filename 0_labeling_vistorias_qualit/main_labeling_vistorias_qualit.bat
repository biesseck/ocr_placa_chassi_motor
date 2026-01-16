@echo off
setlocal EnableExtensions

REM Move to the directory where this .bat file is located
cd /d "%~dp0"

set "CONDA_ENV=labeling_vistorias_qualit"
set "USE_CONDA="

REM Check if Conda is available
where conda >nul 2>&1 && set "USE_CONDA=1"

REM Try to init conda (only if found)
if defined USE_CONDA (
    call conda.bat >nul 2>&1
    if errorlevel 1 set "USE_CONDA="
)

REM Try to activate env (only if init worked)
if defined USE_CONDA (
    call conda activate "%CONDA_ENV%" >nul 2>&1
    if errorlevel 1 set "USE_CONDA="
)

if defined USE_CONDA (
    echo INFO: Using Conda env "%CONDA_ENV%".
) else (
    echo INFO: Conda/env not available. Using system Python...
)

REM Run the Python script (quoted path to avoid parsing issues)
python "%~dp0main_labeling_vistorias_qualit.py"

set "RC=%ERRORLEVEL%"
endlocal & exit /b %RC%
