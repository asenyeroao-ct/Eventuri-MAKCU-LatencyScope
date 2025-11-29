@echo off
chcp 65001 > nul
echo ========================================
echo 創建虛擬環境並安裝依賴套件
echo ========================================
echo.

:: 檢查 Python 是否安裝
python --version >nul 2>&1
if errorlevel 1 (
    echo [錯誤] 未找到 Python，請先安裝 Python 3.8 或更高版本
    pause
    exit /b 1
)

:: 創建虛擬環境
if exist venv (
    echo [資訊] 虛擬環境已存在，將刪除並重新創建...
    rmdir /s /q venv
)

echo [資訊] 正在創建虛擬環境...
python -m venv venv
if errorlevel 1 (
    echo [錯誤] 創建虛擬環境失敗
    pause
    exit /b 1
)

:: 啟動虛擬環境
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo [錯誤] 啟動虛擬環境失敗
    pause
    exit /b 1
)

:: 升級 pip
echo.
echo [資訊] 正在升級 pip...
python -m pip install --upgrade pip

:: 安裝依賴套件
echo.
echo [資訊] 正在安裝依賴套件...
pip install -r requirements.txt
if errorlevel 1 (
    echo [錯誤] 安裝依賴套件失敗
    pause
    exit /b 1
)

echo.
echo ========================================
echo 安裝完成！
echo ========================================
echo.
echo 請執行 run.bat 來啟動程式
echo.
pause

