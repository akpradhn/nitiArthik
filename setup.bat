@echo off
REM Virtual environment setup script for NitiArthik (Windows)

echo ==========================================
echo NitiArthik - Virtual Environment Setup
echo ==========================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH.
    echo Please install Python 3.8 or higher.
    pause
    exit /b 1
)

echo Found Python version:
python --version
echo.

REM Create virtual environment if it doesn't exist
if exist venv (
    echo Virtual environment already exists.
    set /p RECREATE="Do you want to recreate it? (y/N): "
    if /i "%RECREATE%"=="y" (
        echo Removing existing virtual environment...
        rmdir /s /q venv
        echo Creating new virtual environment...
        python -m venv venv
    ) else (
        echo Using existing virtual environment.
    )
) else (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo.
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo.
echo Upgrading pip...
python -m pip install --upgrade pip

REM Install dependencies
echo.
echo Installing dependencies from requirements.txt...
pip install -r requirements.txt

REM Create necessary directories
echo.
echo Creating necessary directories...
if not exist uploads mkdir uploads

REM Create .env file if it doesn't exist
if not exist .env (
    echo.
    echo Creating .env file...
    if exist .env.example (
        copy .env.example .env
        echo Please edit .env file and set your SECRET_KEY
    ) else (
        (
            echo SECRET_KEY=dev-secret-key-change-in-production
            echo DATABASE_URL=sqlite:///nitiarthik.db
        ) > .env
        echo Created .env file with default values. Please update SECRET_KEY for production.
    )
)

echo.
echo ==========================================
echo Setup completed successfully!
echo ==========================================
echo.
echo To activate the virtual environment manually, run:
echo   venv\Scripts\activate.bat
echo.
echo To run the application:
echo   python app.py
echo.
pause





