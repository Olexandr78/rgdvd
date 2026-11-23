@echo off
setlocal
cd /d "%~dp0"

echo ============================================
echo RGDVD - OFFLINE WINDOWS / DVD BUILD
echo ============================================

python --version
if errorlevel 1 (
    echo Python 3.10+ is required to BUILD the game.
    pause
    exit /b 1
)

python -m pip install --upgrade pip
if errorlevel 1 goto :failed
python -m pip install -r requirements.txt pyinstaller
if errorlevel 1 goto :failed

if exist build rmdir /s /q build
if exist dist\RGDVD rmdir /s /q dist\RGDVD

python -m PyInstaller --noconfirm --clean --onedir --console ^
  --name RGDVD ^
  --collect-all panda3d ^
  --collect-all direct ^
  --hidden-import websocket ^
  --add-data "rgdvd;rgdvd" ^
  main.py
if errorlevel 1 goto :failed

copy /y README.md dist\RGDVD\README.md >nul
if errorlevel 1 goto :failed

python tools\check_dvd_size.py dist\RGDVD
if errorlevel 1 goto :failed

where oscdimg >nul 2>nul
if errorlevel 1 (
    echo.
    echo Game folder is ready in dist\RGDVD.
    echo oscdimg was not found, so an ISO was not created.
    echo Install Windows ADK Deployment Tools to create an ISO.
    goto :success
)

if exist RGDVD.iso del RGDVD.iso
oscdimg -m -o -u2 -udfver102 dist\RGDVD RGDVD.iso
if errorlevel 1 goto :failed

echo.
echo ISO created: RGDVD.iso
for %%I in (RGDVD.iso) do echo ISO size: %%~zI bytes

:success
echo.
echo BUILD COMPLETE
pause
exit /b 0

:failed
echo.
echo BUILD FAILED. Read the error above.
pause
exit /b 1
