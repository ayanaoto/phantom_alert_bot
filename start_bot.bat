@echo off
title Phantom Alert Bot Launcher

REM --- このバッチファイルがあるディレクトリに移動 ---
cd /d "%~dp0"

echo. 
echo --- Activating Virtual Environment...
REM --- 仮想環境を有効にする ---
call .\venv\Scripts\activate.bat

REM --- 仮想環境の有効化チェック ---
if %errorlevel% neq 0 (
    echo.
    echo FATAL ERROR: Could not activate virtual environment.
    pause
    exit /b
)
echo Environment activated successfully.
echo.

echo --- Launching Phantom Alert Bot... ---
echo.

REM ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
REM 
REM 　以下のコマンドで、仮想環境内の正しいpython.exeを直接指定してsplash.pyを起動します。
REM 　これが、バッチファイルが一瞬で消える問題に対する、最も確実な解決策です。
REM 
REM ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
.\venv\Scripts\python.exe splash.py

echo.
echo --- Launcher script finished. ---
pause