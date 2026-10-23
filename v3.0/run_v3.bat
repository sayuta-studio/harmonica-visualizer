@echo off
cd /d "%~dp0"

where python >nul 2>nul
if %ERRORLEVEL% equ 0 (
    python main.py
    goto end
)

where py >nul 2>nul
if %ERRORLEVEL% equ 0 (
    py -3 main.py
    goto end
)

echo [ERROR] Python not found in PATH.
pause

:end
if %ERRORLEVEL% neq 0 (
    echo.
    echo ========================================
    echo An error occurred during execution.
    echo ========================================
    pause
)