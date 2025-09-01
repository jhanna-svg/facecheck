@echo off
cd /d C:\FaceRecognition

echo Starting FaceRecognition server...
echo (%DATE% %TIME%) > app_log.txt

if not exist app.py (
  echo ERROR: app.py not found in %CD% >> app_log.txt
  echo ERROR: app.py not found in %CD%
  pause
  exit /b 1
)

if not exist .venv\Scripts\activate (
  echo ERROR: .venv not found or missing activation script >> app_log.txt
  echo ERROR: .venv not found or missing activation script
  pause
  exit /b 1
)

REM Activate venv
call .venv\Scripts\activate

REM Run app with proper signal handling (no output redirection)
echo Running FaceCheck server...
echo Press CTRL+C to stop the server gracefully
echo.
python app.py

echo.
echo Server has been stopped.
echo (%DATE% %TIME%) Server stopped >> app_log.txt
echo.

REM Show recent log if it exists
if exist app_log.txt (
    echo Recent log entries:
    powershell -NoProfile -Command "Get-Content -Path 'app_log.txt' -Tail 10"
)

echo.
echo Press any key to exit...
pause > nul
