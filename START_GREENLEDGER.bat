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

REM ---- Start Module 0 ----
echo Starting Module 0...
start "GreenLedger - Module 0" cmd /k ^
cd /d "%~dp0module0" ^&^& ^
".venv\Scripts\python.exe" -m uvicorn app:app --host 0.0.0.0 --port 8000

REM ---- Give Module 0 time to start ----
timeout /t 4 /nobreak >nul

REM ---- Start Module 1 ----
echo Starting Module 1...
start "GreenLedger - Module 1" cmd /k ^
cd /d "%~dp0module1" ^&^& ^
".venv\Scripts\python.exe" module1.py

REM ---- Open browser ----
timeout /t 3 /nobreak >nul
start "" "http://127.0.0.1:8000"

echo.
echo ==========================================
echo GreenLedger started.
echo ==========================================
echo Module 0: http://127.0.0.1:8000
echo.
echo You can close this launcher window.
echo The Module 0 and Module 1 windows will remain open.
echo ==========================================
pause