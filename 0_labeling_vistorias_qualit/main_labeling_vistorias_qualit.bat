@echo off
setlocal

REM Move to the directory where this .bat file is located
cd /d "%~dp0"

REM Check if Conda is available
where conda >nul 2>&1
if errorlevel 1 (
    echo ERROR: Conda is not installed or not in PATH.
    echo Please install Anaconda/Miniconda or add it to PATH.
    pause
    exit /b 1
)

REM Initialize Conda for batch usage (needed for activation)
call conda.bat >nul 2>&1

REM Activate the "labeling_vistorias_qualit" environment
call conda activate labeling_vistorias_qualit
if errorlevel 1 (
    echo ERROR: Conda environment "labeling_vistorias_qualit" not found.
    echo Available environments:
    conda env list
    pause
    exit /b 1
)

REM Run the Python script
python .\main_labeling_vistorias_qualit.py

REM pause
endlocal
