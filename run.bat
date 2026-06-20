@echo off
title PrismFlow - AI Meeting Assistant
cd /d "%~dp0"

echo [PrismFlow] Activating virtual environment...
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
) else (
    echo [ERROR] Virtual environment .venv not found. Please run setup first.
    pause
    exit /b 1
)

echo [PrismFlow] Launching application...
python main.py
if %errorlevel% neq 0 (
    echo [ERROR] Application exited with error code %errorlevel%.
    pause
)
