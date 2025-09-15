@echo off
chcp 65001 > nul
cls

REM Activate virtual environment
call "C:\Users\pc\OneDrive\Desktop\phantom_alert_bot\venv\Scripts\activate.bat"

REM Run the Python script
python app.py

REM Deactivate virtual environment (optional)
REM deactivate

echo.
echo Phantom Alert Bot has finished execution.
pause