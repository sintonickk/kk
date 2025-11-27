@echo off
setlocal

:: Go to the parent directory of the script
cd /d "%~dp0../kk"

:: Run main.py
python -m main

endlocal