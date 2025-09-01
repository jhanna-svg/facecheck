@echo off
title Stop FaceCheck Server
echo =================================
echo   Emergency Server Stop Tool
echo =================================
echo.

echo Attempting to stop FaceCheck server...
echo.

REM Kill any Python processes running Flask/FaceCheck
echo Stopping Python processes on port 5000...
netstat -ano | findstr :5000 > nul
if %errorlevel% == 0 (
    echo Found processes using port 5000, attempting to stop...
    for /f "tokens=5" %%i in ('netstat -ano ^| findstr :5000') do (
        echo Killing process ID: %%i
        taskkill /PID %%i /F > nul 2>&1
    )
) else (
    echo No processes found using port 5000
)

REM Kill any stuck Python processes
echo Stopping any remaining Python processes...
taskkill /F /IM python.exe > nul 2>&1
taskkill /F /IM pythonw.exe > nul 2>&1

REM Clean up any OpenCV windows
echo Cleaning up OpenCV windows...
taskkill /F /IM opencv_world*.exe > nul 2>&1

echo.
echo ==========================================
echo     SERVER STOP PROCESS COMPLETED
echo ==========================================
echo.
echo All FaceCheck related processes should now be stopped.
echo You can safely restart the server using start.bat or run_server.bat
echo.

pause
