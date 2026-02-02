@echo off
setlocal ENABLEEXTENSIONS

REM Change to ranqi_server root (this script is in ranqi_server\app\)
set "SCRIPT_DIR=%~dp0"
echo [TRACE] SCRIPT_DIR=%SCRIPT_DIR%
cd /d "%SCRIPT_DIR%.."
if errorlevel 1 goto :cd_fail

REM Prefer current env python (Conda/virtualenv), then python, then py, then python3
set "PYEXE="
echo [TRACE] Detecting Python interpreter...

REM If running under Conda, prefer its python.exe
if defined CONDA_PREFIX if exist "%CONDA_PREFIX%\python.exe" set "PYEXE=%CONDA_PREFIX%\python.exe"
if defined PYEXE goto :py_found

REM If running under virtualenv, prefer its python.exe
if defined VIRTUAL_ENV if exist "%VIRTUAL_ENV%\Scripts\python.exe" set "PYEXE=%VIRTUAL_ENV%\Scripts\python.exe"
if defined PYEXE goto :py_found

echo [TRACE] Detecting python on PATH...
where python >nul 2>nul
if not errorlevel 1 set "PYEXE=python"
if defined PYEXE goto :py_found

echo [TRACE] Detecting py launcher on PATH...
where py >nul 2>nul
if not errorlevel 1 set "PYEXE=py"
if defined PYEXE goto :py_found

echo [TRACE] Detecting python3 on PATH...
where python3 >nul 2>nul
if not errorlevel 1 set "PYEXE=python3"
if defined PYEXE goto :py_found

echo Could not find Python interpreter (py/python/python3) in PATH.
exit /b 1

:py_found
echo [TRACE] Using Python: %PYEXE%
"%PYEXE%" -V
"%PYEXE%" -u main.py
set EXITCODE=%ERRORLEVEL%
if %EXITCODE% NEQ 0 echo Application exited with code %EXITCODE%.
exit /b %EXITCODE%

:cd_fail
echo Failed to change directory to project root.
exit /b 1
