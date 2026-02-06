@echo off
chcp 65001 > nul
echo ========================================
echo Creating Virtual Environment and Installing Dependencies
echo ========================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found, please install Python 3.8 or higher
    pause
    exit /b 1
)

:: Create virtual environment
if exist "venv" (
    echo [INFO] Virtual environment already exists, removing and recreating...
    rmdir /s /q "venv"
)

echo [INFO] Creating virtual environment...
python -m venv "venv"
if errorlevel 1 (
    echo [ERROR] Failed to create virtual environment
    pause
    exit /b 1
)

:: Activate virtual environment
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

:: Upgrade pip
echo.
echo [INFO] Upgrading pip...
python -m pip install --upgrade pip

:: Install dependencies
echo.
echo [INFO] Installing dependencies...
pip install -r "requirements.txt"
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo ========================================
echo Installation Complete!
echo ========================================
echo.
echo Please run run.bat to start the program
echo.
pause

