@echo off
setlocal enabledelayedexpansion

REM Build alarm_server/app.py into a single-file exe using PyInstaller
REM Usage: double-click this file or run in cmd

REM Resolve directories
set "PACK_DIR=%~dp0"
for %%I in ("%PACK_DIR%..\") do set "PROJECT_DIR=%%~fI"
cd /d "%PROJECT_DIR%"

REM Ensure Python is available
where py >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python launcher 'py' not found in PATH.
  echo Please install Python 3 and ensure the 'py' launcher is available.
  exit /b 1
)

REM Ensure PyInstaller is installed
py -m pyinstaller --version >nul 2>nul
if errorlevel 1 (
  echo [INFO] Installing PyInstaller...
  py -m pip install --upgrade pip >nul 2>nul
  py -m pip install pyinstaller || (
    echo [ERROR] Failed to install PyInstaller.
    exit /b 1
  )
)

if errorlevel 1 (
  echo [ERROR] Failed to ensure Flask is installed.
  exit /b 1
)

set "NAME=alarm_server"
set "ENTRY=app.py"

if not exist "%ENTRY%" (
  echo [ERROR] Entry file not found: %ENTRY%
  exit /b 1
)

REM Clean previous build artifacts
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist %NAME%.spec del /f /q %NAME%.spec

REM Include static assets required at runtime
set "ADD_DATA=--add-data index.html;. --add-data logo.png;."

REM Build one-folder app so static files are next to the exe
py -m PyInstaller --noconfirm --clean --onedir --name %NAME% %ADD_DATA% "%ENTRY%"
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" (
  echo [ERROR] PyInstaller build failed with code %RC%.
  exit /b %RC%
)

echo [OK] Build complete. Output folder: dist\%NAME%\
echo Run: dist\%NAME%\%NAME%.exe
exit /b 0
