@echo off
setlocal
cd /d "%~dp0"

python --version
if errorlevel 1 (
    echo Python 3.10+ was not found. Install it first.
    pause
    exit /b 1
)

python -c "import panda3d, websocket, customtkinter" >nul 2>nul
if errorlevel 1 (
    echo Installing RGDVD dependencies...
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
