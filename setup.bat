@echo off
:: ============================================================
:: FraudLens — One-Click Setup (Windows Batch)
:: Double-click this file OR run from CMD to set up the project.
:: ============================================================

echo.
echo ======================================
echo    FraudLens -- Project Setup
echo ======================================
echo.

:: Step 1: Check Python
echo [1/6] Checking Python version...
python --version >nul 2>&1
if errorlevel 1 (
    echo   ERROR: Python not found! Install Python 3.11+ from https://python.org
    pause
    exit /b 1
)
python --version
echo   OK: Python found.

:: Step 2: Create venv
echo.
echo [2/6] Creating virtual environment...
if exist "venv\" (
    echo   OK: venv already exists, skipping.
) else (
    python -m venv venv
    echo   OK: Virtual environment created.
)

:: Step 3: Activate
echo.
echo [3/6] Activating virtual environment...
call venv\Scripts\activate.bat
echo   OK: venv activated.

:: Step 4: Upgrade pip
echo.
echo [4/6] Upgrading pip...
python -m pip install --upgrade pip --quiet
echo   OK: pip upgraded.

:: Step 5: Install dependencies
echo.
echo [5/6] Installing all dependencies from requirements.txt...
echo   (This may take 2-3 minutes on first run...)
pip install -r requirements.txt
if errorlevel 1 (
    echo   ERROR: Dependency installation failed. Check requirements.txt
    pause
    exit /b 1
)
echo   OK: All dependencies installed!

:: Step 6: Setup .env
echo.
echo [6/6] Setting up .env file...
if exist ".env" (
    echo   OK: .env already exists.
) else (
    copy ".env.example" ".env" >nul
    echo   OK: .env created from .env.example
    echo   IMPORTANT: Edit .env with your TigerGraph + OpenAI credentials!
)

:: Done
echo.
echo ======================================
echo    Setup Complete!
echo ======================================
echo.
echo Next steps:
echo   1. Edit .env with your credentials
echo   2. python scripts\load_schema.py
echo   3. python scripts\load_data.py --sample 10000
echo   4. uvicorn backend.main:app --reload --port 8000
echo.
echo To activate venv next time:
echo   venv\Scripts\activate.bat
echo.
pause
