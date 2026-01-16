@echo off
setlocal

REM Move to the directory of this install.bat
cd /d "%~dp0"

REM Install Python requirements
echo Installing Python dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install requirements.
    pause
    exit /b 1
)

REM Create shortcut on current user's Desktop
echo Creating Desktop shortcut...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$desktop=[Environment]::GetFolderPath('Desktop'); $name='Labeling Vistorias Qualit'; $target=Join-Path '%~dp0' 'main_labeling_vistorias_qualit.bat'; $lnk=Join-Path $desktop ($name + '.lnk'); $w=New-Object -ComObject WScript.Shell; $s=$w.CreateShortcut($lnk); $s.TargetPath=$target; $s.WorkingDirectory='%~dp0'; $s.IconLocation=Join-Path '%~dp0' 'assets/license.ico'; $s.Save()"
if errorlevel 1 (
    echo ERROR: Failed to create shortcut.
    pause
    exit /b 1
)

echo.
echo Installation completed successfully.
pause
endlocal
