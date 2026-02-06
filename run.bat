@echo off
chcp 65001 > nul
echo ========================================
echo Starting Color Detection Auto-Click Program
echo ========================================
echo.

if not exist venv (
    echo [ERROR] Virtual environment not found, please run setup.bat first
    pause
    exit /b 1
)

if not exist "venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment script not found
    pause
    exit /b 1
)
call "venv\Scripts\activate.bat"
if errorlevel 1 (
    echo [ERROR] Failed to activate virtual environment
    pause
    exit /b 1
)

echo [INFO] Starting program...
python main.py
if errorlevel 1 (
    echo.
    echo [ERROR] Program execution failed
    pause
    exit /b 1
)

pause

