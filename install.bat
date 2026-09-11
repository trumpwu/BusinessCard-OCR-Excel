@echo off
title BusinessCard-OCR-Excel 一鍵安裝與環境配置
echo ========================================================
echo   BusinessCard-OCR-Excel 一鍵安裝與環境配置
echo ========================================================
echo.
cd /d "%~dp0"
echo [*] 正在檢查 Python 環境...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [警告] 系統未安裝預設 Python，正在嘗試使用內嵌 Python...
    set "PY_CMD=C:\Users\Innovare\google-cloud-sdk\platform\bundledpython\python.exe"
) else (
    set "PY_CMD=python"
)
echo [*] 使用 Python: %PY_CMD%
echo.
echo [*] 正在安裝必要套件 (PyMuPDF, OpenCV, OpenPyXL, Pillow)...
"%PY_CMD%" -m pip install -r requirements.txt
echo.
echo [*] 正在檢查本地 OCR 核心引擎...
if not exist "D:\project\Umi-OCR\Umi-OCR_Paddle_v2.1.5\UmiOCR-data\plugins\win7_x64_PaddleOCR-json\PaddleOCR-json.exe" (
    echo [*] 未偵測到 OCR 引擎，正在從 GitHub 下載 Umi-OCR 綠色引擎套件 (約 128MB)...
    if not exist "engine" mkdir "engine"
    curl -L -o "engine\Umi-OCR_Paddle_v2.1.5.7z.exe" "https://github.com/hiroi-sora/Umi-OCR/releases/download/v2.1.5/Umi-OCR_Paddle_v2.1.5.7z.exe"
    echo [*] 正在解壓縮 OCR 引擎...
    start /wait "" "engine\Umi-OCR_Paddle_v2.1.5.7z.exe" -y -o"engine"
) else (
    echo [OK] 已偵測到本地 PaddleOCR-json 核心引擎！
)
echo.
echo ========================================================
echo   ?? 安裝完成！現在您可以直接使用 【一鍵名片自動歸檔】.bat
echo ========================================================
echo.
pause
