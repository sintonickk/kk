@echo off
setlocal

:: Check if folder path is provided
if "%~1"=="" (
    echo Error: Please provide a folder path
    echo Usage: %~nx0 "path\to\folder"
    exit /b 1
)

:: Go to the parent directory of the script
cd /d "%~dp0../kk"

:: Run main_folder.py with the provided folder path
python -m main_folder "%~1"

endlocal