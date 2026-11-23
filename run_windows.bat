@echo off
setlocal
cd /d "%~dp0"

python --version
if errorlevel 1 (
    echo Python was not found. Install Python 3.10 or newer first.
    pause
    exit /b 1
)

python -c "import panda3d" >nul 2>nul
if errorlevel 1 (
    echo Panda3D is missing. Installing the game dependency...
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo Dependency installation failed.
        pause
        exit /b 1
    )
)

python main.py
if errorlevel 1 (
    echo.
    echo RGDVD closed with an error. Check the console message above.
    pause
)
endlocal
