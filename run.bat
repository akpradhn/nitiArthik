@echo off
REM Quick start script for NitiArthik (Windows)
REM This script assumes the virtual environment is already set up.
REM Run setup.bat first if you haven't set up the environment yet.

REM Check if virtual environment exists
if not exist venv (
    echo Virtual environment not found!
    echo Please run setup.bat first to set up the environment.
    pause
    exit /b 1
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Check if dependencies are installed
python -c "import flask" >nul 2>&1
if errorlevel 1 (
    echo Dependencies not installed. Installing...
    pip install -r requirements.txt
)

REM Create uploads directory if it doesn't exist
if not exist uploads mkdir uploads

REM Run the application
echo.
echo Starting NitiArthik application...
echo Access the application at http://localhost:5000
echo.
python app.py





