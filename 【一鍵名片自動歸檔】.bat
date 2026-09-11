@echo off
title 名片一鍵自動歸檔系統
echo ========================================================
echo   名片一鍵自動裁切與歸檔系統 (100%% 離線 / 0 Token)
echo ========================================================
echo.
echo   正在啟動本地 OCR 與名片分析管線，請稍候...
echo.
cd /d "%~dp0"
python --version >nul 2>&1
if %errorlevel% neq 0 (
    set "PYTHON_EXE=C:\Users\Innovare\google-cloud-sdk\platform\bundledpython\python.exe"
) else (
    set "PYTHON_EXE=python"
)
set "SCRIPT=%~dp0main.py"
if "%~1"=="" (
    "%PYTHON_EXE%" "%SCRIPT%"
) else (
    "%PYTHON_EXE%" "%SCRIPT%" "%~1"
)
echo.
echo ========================================================
echo   處理完成！已輸出至 D:\名片\
echo ========================================================
echo.
pause
