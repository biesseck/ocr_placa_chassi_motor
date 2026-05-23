@echo off
setlocal EnableExtensions

REM Move to the directory of this install.bat
cd /d "%~dp0"

set "CONDA_ENV=licenseplate_ocr_api_py310"
set "USE_CONDA="

REM Check if Conda is available
where conda >nul 2>&1 && set "USE_CONDA=1"

REM Try to activate env (only if init worked)
if defined USE_CONDA (
    echo Creating conda env: %CONDA_ENV%
    conda create -n "%CONDA_ENV%" python=3.10 -y

    echo Activating conda env: %CONDA_ENV%
    conda activate "%CONDA_ENV%" >nul 2>&1
    
    REM Install Python requirements
    echo Installing Python dependencies...
    pip3 install --ignore-installed --force-reinstall -r requirements.txt
    echo Installation completed successfully.

) else (
    echo ERROR: Anaconda not available. Install it first.
)

pause
endlocal
