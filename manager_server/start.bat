@echo off
setlocal
set ROOT=%CD%
set PORT=8001
uvicorn app.main:app --reload --host 0.0.0.0 --port %PORT% --app-dir "%ROOT%"
endlocal
pause
