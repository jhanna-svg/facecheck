@echo off
title FaceCheck Server
cd /d C:\FaceRecognition

echo =================================
echo    FaceCheck Server Launcher
echo =================================
echo.

REM Check if app.py exists
if not exist app.py (
    echo ERROR: app.py not found in %CD%
    echo Please make sure you're in the correct directory.
    pause
    exit /b 1
)

REM Check virtual environment
if not exist .venv\Scripts\activate (
    echo ERROR: Virtual environment not found
    echo Please create a virtual environment first.
    pause
    exit /b 1
)

REM Activate virtual environment
echo Activating virtual environment...
call .venv\Scripts\activate

REM Show current configuration
echo.
echo Virtual Environment: ACTIVE
echo Python Path: %VIRTUAL_ENV%
echo Server Host: 0.0.0.0:5000
echo.

REM Start server with immediate output (no redirection)
echo Starting FaceCheck server...
echo.
echo ==========================================
echo  SERVER IS RUNNING - Press CTRL+C to stop
echo ==========================================
echo.

REM Run Python directly without output redirection for proper CTRL+C handling
python app.py

REM This section runs after server stops
echo.
echo ==========================================
echo        SERVER HAS BEEN STOPPED
echo ==========================================
echo Server stopped at: %DATE% %TIME%
echo.

REM Deactivate virtual environment
deactivate

echo Press any key to close this window...
pause > nul
