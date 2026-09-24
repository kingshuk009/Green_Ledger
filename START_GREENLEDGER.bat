@echo off
setlocal

cd /d "%~dp0"

echo ==========================================
echo       GREENLEDGER STARTING...
echo ==========================================
echo.

REM ---- Check Module 0 environment ----
if not exist "%~dp0module0\.venv\Scripts\python.exe" (
    echo ERROR: Module 0 Python environment not found.
    pause
    exit /b 1
)

REM ---- Check Module 1 environment ----
if not exist "%~dp0module1\.venv\Scripts\python.exe" (
    echo ERROR: Module 1 Python environment not found.
    pause
    exit /b 1
)

REM ---- Check Dashboard environment ----
if not exist "%~dp0dashboard\.venv\Scripts\python.exe" (
    echo ERROR: Dashboard Python environment not found.
    pause
    exit /b 1
)

REM ---- Start Module 0 ----
echo Starting Module 0 (Farm Registration)...
start "GreenLedger - Module 0" cmd /k ^
cd /d "%~dp0module0" ^&^& ^
".venv\Scripts\python.exe" -m uvicorn app:app --host 0.0.0.0 --port 8000

REM ---- Give Module 0 time to start ----
timeout /t 5 /nobreak >nul

REM ---- Start Module 1 ----
echo Starting Module 1 (Satellite MRV)...
start "GreenLedger - Module 1" cmd /k ^
cd /d "%~dp0module1" ^&^& ^
".venv\Scripts\python.exe" module1.py

REM ---- Start Dashboard ----
echo Starting Dashboard...
start "GreenLedger - Dashboard" cmd /k ^
cd /d "%~dp0dashboard" ^&^& ^
".venv\Scripts\python.exe" dashboard_server.py

REM ---- Give all services time to start ----
timeout /t 5 /nobreak >nul

REM ---- Open browser tabs ----
echo Opening browser...
start "" "http://127.0.0.1:8000"
timeout /t 2 /nobreak >nul
start "" "http://127.0.0.1:8010/static/index.html?farm_id=FARM_20260901171202851780"

echo.
echo ==========================================
echo  GreenLedger is running!
echo ==========================================
echo  Farm Registration : http://127.0.0.1:8000
echo  Dashboard         : http://127.0.0.1:8010/static/index.html
echo  Module 1          : Running in background
echo ==========================================
echo.
echo  To stop: close all 3 terminal windows
echo  or double-click STOP_GREENLEDGER.bat
echo ==========================================
pause