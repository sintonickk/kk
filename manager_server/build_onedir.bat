@echo off
setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%"
set "DIST_DIR=%PROJECT_ROOT%\dist"
set "BUILD_DIR=%PROJECT_ROOT%\build"
set "OUTPUT_DIR=%DIST_DIR%\manager_server"
set "OUTPUT_NAME=manager_server"

:: Create necessary directories
if not exist "%DIST_DIR%" mkdir "%DIST_DIR%"
if not exist "%BUILD_DIR%" mkdir "%BUILD_DIR%"

echo [%TIME%] Starting onedir build...

:: Stop any running instances
taskkill /F /IM "%OUTPUT_NAME%.exe" /T >nul 2>&1

cd /d "%PROJECT_ROOT%"

echo [%TIME%] Installing build requirements...
pip install -r requirements-build.txt

echo [%TIME%] Running PyInstaller (onedir)...

set PYTHONPATH=%PROJECT_ROOT%
python -m PyInstaller ^
    --name "%OUTPUT_NAME%" ^
    --onedir ^
    --console ^
    --noconfirm ^
    --workpath "%BUILD_DIR%" ^
    --distpath "%DIST_DIR%" ^
    --hidden-import fastapi ^
    --hidden-import uvicorn ^
    --hidden-import uvicorn.lifespan.on ^
    --hidden-import uvicorn.lifespan.off ^
    --hidden-import uvicorn.protocols.http.h11_impl ^
    --hidden-import uvicorn.protocols.websockets.auto ^
    --hidden-import uvicorn._types ^
    --hidden-import uvicorn.logging ^
    --hidden-import uvicorn.loops ^
    --hidden-import uvicorn.loops.auto ^
    --hidden-import uvicorn.loops.uvloop ^
    --hidden-import uvicorn.loops.asyncio ^
    --hidden-import sqlalchemy ^
    --hidden-import sqlalchemy.dialects.postgresql ^
    --hidden-import sqlalchemy.dialects.postgresql.psycopg2 ^
    --hidden-import psycopg2 ^
    --hidden-import pydantic ^
    --hidden-import passlib ^
    --hidden-import passlib.handlers.bcrypt ^
    --hidden-import bcrypt ^
    --hidden-import yaml ^
    --hidden-import imagededup ^
    --hidden-import PIL ^
    --hidden-import numpy ^
    --hidden-import scipy ^
    --hidden-import jaraco.text ^
    --hidden-import jaraco.context ^
    --hidden-import jaraco.functools ^
    --hidden-import importlib_metadata ^
    --hidden-import platformdirs ^
    --hidden-import six ^
    --hidden-import pytz ^
    --hidden-import tzdata ^
    --add-data "config;config" ^
    --add-data "routes.json;." ^
    run_server.py

if errorlevel 1 (
    echo [%TIME%] Error: Build failed with code: %errorlevel%
    pause
    exit /b %errorlevel%
)

:: Copy config files if not already bundled
if exist "%PROJECT_ROOT%\config" (
    echo [%TIME%] Copying config files...
    xcopy /E /I /Y "%PROJECT_ROOT%\config" "%OUTPUT_DIR%\config"
)

:: Copy routes.json if exists
if exist "%PROJECT_ROOT%\routes.json" (
    echo [%TIME%] Copying routes.json...
    copy /Y "%PROJECT_ROOT%\routes.json" "%OUTPUT_DIR%\"
)

if exist "%OUTPUT_DIR%\%OUTPUT_NAME%.exe" (
    echo [%TIME%] Build completed successfully!
    echo Output directory: %OUTPUT_DIR%
    echo.
    echo To run the application:
    echo   %OUTPUT_DIR%\%OUTPUT_NAME%.exe
    echo.
    echo Remember to ensure config\config.yaml and routes.json are present next to the exe.
) else (
    echo [%TIME%] Error: Output file not found: %OUTPUT_DIR%\%OUTPUT_NAME%.exe
    exit /b 1
)

echo [%TIME%] Done!
pause
