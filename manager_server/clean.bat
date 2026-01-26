@echo off
setlocal

echo Cleaning build artifacts...

if exist "build" (
    rmdir /s /q "build"
    echo Removed build/
)

if exist "dist" (
    rmdir /s /q "dist"
    echo Removed dist/
)

if exist "*.spec" (
    del /q *.spec
    echo Removed *.spec files
)

echo Clean complete.
pause
