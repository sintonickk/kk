@echo off
setlocal

REM Start the watchdog for manager_server in a detached PowerShell window
REM Adjust paths below if your install paths differ
set WATCHDOG_PS1=D:\yjq\watch_dog\watchdog.ps1
set START_SCRIPT=D:\yjq\manager_server\start.bat
set LOG_FILE=D:\yjq\watch_dog\watchdog.log

if not exist "%WATCHDOG_PS1%" (
  echo Watchdog script not found: %WATCHDOG_PS1%
  exit /b 1
)

if not exist "%START_SCRIPT%" (
  echo Start script not found: %START_SCRIPT%
  exit /b 1
)

REM Use START to detach so this BAT exits immediately
start "watchdog_manager_server" powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%WATCHDOG_PS1%" -ProcessName "manager_server" -StartScript "%START_SCRIPT%" -CheckInterval 10 -LogPath "%LOG_FILE%"

endlocal
exit /b 0
