@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM ============================================================
REM GreenLedger - Full Pipeline Launcher
REM Project root: D:\GL
REM
REM IMPORTANT:
REM - Module 0 and Module 1 are NOT rebuilt or modified.
REM - This launcher only starts/runs the existing components.
REM - If your local entry-point filename differs, the launcher
REM   searches common names and then stops with a clear message.
REM ============================================================

title GreenLedger - Full Pipeline

set "GL_ROOT=D:\GL"
set "PYTHON=python"
set "CONDA_ENV=GreenLedger"

echo.
echo ============================================================
echo                 GREENLEDGER FULL PIPELINE
echo ============================================================
echo Root: %GL_ROOT%
echo.

if not exist "%GL_ROOT%" (
    echo [ERROR] GreenLedger folder was not found:
    echo         %GL_ROOT%
    echo.
    pause
    exit /b 1
)

cd /d "%GL_ROOT%"

REM ------------------------------------------------------------
REM 1. Select Python
REM ------------------------------------------------------------
where conda >nul 2>&1
if %errorlevel%==0 (
    echo [INFO] Conda detected. Trying environment: %CONDA_ENV%
    call conda activate %CONDA_ENV% >nul 2>&1
)

where python >nul 2>&1
if not %errorlevel%==0 (
    echo [ERROR] Python was not found in PATH/Conda environment.
    echo Activate your GreenLedger environment and run this file again.
    pause
    exit /b 1
)

echo [OK] Python:
python --version
echo.

REM ------------------------------------------------------------
REM 2. Basic dependency check
REM ------------------------------------------------------------
echo ============================================================
echo [1/5] CHECKING PYTHON DEPENDENCIES
echo ============================================================

python -c "import fastapi,uvicorn,numpy; print('[OK] FastAPI/Uvicorn/NumPy available')" >nul 2>&1
if errorlevel 1 (
    echo [WARNING] One or more core Python packages are missing.
    echo Attempting to continue because your project may use a local environment.
)

echo.

REM ------------------------------------------------------------
REM 3. Start Module 0 API
REM ------------------------------------------------------------
echo ============================================================
echo [2/5] STARTING MODULE 0
echo ============================================================

set "M0_DIR=%GL_ROOT%\module0"

if not exist "%M0_DIR%" (
    echo [ERROR] Module 0 directory not found:
    echo         %M0_DIR%
    pause
    exit /b 1
)

set "M0_ENTRY="

if exist "%M0_DIR%\app.py" set "M0_ENTRY=app.py"
if not defined M0_ENTRY if exist "%M0_DIR%\main.py" set "M0_ENTRY=main.py"
if not defined M0_ENTRY if exist "%M0_DIR%\api.py" set "M0_ENTRY=api.py"

if not defined M0_ENTRY (
    echo [ERROR] Could not find Module 0 entry point.
    echo Expected one of:
    echo   module0\app.py
    echo   module0\main.py
    echo   module0\api.py
    pause
    exit /b 1
)

echo [OK] Module 0 entry point: %M0_ENTRY%
echo [INFO] Starting API on http://127.0.0.1:8000

start "GreenLedger - Module 0 API" cmd /k ^
    "cd /d "%M0_DIR%" && python -m uvicorn %M0_ENTRY:.py=%:app --host 127.0.0.1 --port 8000"

timeout /t 4 /nobreak >nul

REM ------------------------------------------------------------
REM 4. Run Module 1
REM ------------------------------------------------------------
echo.
echo ============================================================
echo [3/5] RUNNING MODULE 1
echo ============================================================

set "M1_DIR=%GL_ROOT%\module1"

if not exist "%M1_DIR%" (
    echo [ERROR] Module 1 directory not found:
    echo         %M1_DIR%
    echo.
    echo Module 0 was started, but the full pipeline cannot continue.
    pause
    exit /b 1
)

REM Try common Module 1 entry points.
set "M1_ENTRY="

if exist "%M1_DIR%\main.py" set "M1_ENTRY=main.py"
if not defined M1_ENTRY if exist "%M1_DIR%\app.py" set "M1_ENTRY=app.py"
if not defined M1_ENTRY if exist "%M1_DIR%\run.py" set "M1_ENTRY=run.py"
if not defined M1_ENTRY if exist "%M1_DIR%\pipeline.py" set "M1_ENTRY=pipeline.py"
if not defined M1_ENTRY if exist "%M1_DIR%\module1.py" set "M1_ENTRY=module1.py"

if not defined M1_ENTRY (
    echo [WARNING] No common Module 1 launcher was found.
    echo.
    echo The existing Module 1 may be notebook/script based.
    echo Please place its actual launcher name in this BAT:
    echo     M1_ENTRY=your_script.py
    echo.
    echo Module 0 remains running.
    pause
    exit /b 1
)

echo [OK] Module 1 entry point: %M1_ENTRY%
echo [INFO] Running Module 1...

cd /d "%M1_DIR%"
python "%M1_ENTRY%"

if errorlevel 1 (
    echo.
    echo [ERROR] Module 1 failed.
    echo Module 0 is still running in its separate window.
    pause
    exit /b 1
)

cd /d "%GL_ROOT%"

REM ------------------------------------------------------------
REM 5. Run Carbon Asset / MRV pipeline
REM ------------------------------------------------------------
echo.
echo ============================================================
echo [4/5] RUNNING CARBON ASSET / MRV PIPELINE
echo ============================================================

REM Search common downstream launcher locations.
set "CARBON_ENTRY="

if exist "%GL_ROOT%\run_pipeline.py" set "CARBON_ENTRY=%GL_ROOT%\run_pipeline.py"
if not defined CARBON_ENTRY if exist "%GL_ROOT%\run_carbon_asset.py" set "CARBON_ENTRY=%GL_ROOT%\run_carbon_asset.py"
if not defined CARBON_ENTRY if exist "%GL_ROOT%\run_mrv.py" set "CARBON_ENTRY=%GL_ROOT%\run_mrv.py"
if not defined CARBON_ENTRY if exist "%GL_ROOT%\carbon\run.py" set "CARBON_ENTRY=%GL_ROOT%\carbon\run.py"
if not defined CARBON_ENTRY if exist "%GL_ROOT%\mrv\run.py" set "CARBON_ENTRY=%GL_ROOT%\mrv\run.py"
if not defined CARBON_ENTRY if exist "%GL_ROOT%\carbon_asset\run.py" set "CARBON_ENTRY=%GL_ROOT%\carbon_asset\run.py"

if defined CARBON_ENTRY (
    echo [OK] Carbon/MRV launcher: %CARBON_ENTRY%
    python "%CARBON_ENTRY%"

    if errorlevel 1 (
        echo.
        echo [ERROR] Carbon Asset / MRV pipeline failed.
        pause
        exit /b 1
    )
) else (
    echo [WARNING] No common Carbon Asset/MRV launcher was found.
    echo.
    echo The existing components were NOT modified.
    echo If your carbon pipeline uses another filename, set:
    echo     CARBON_ENTRY=path\to\script.py
    echo.
)

REM ------------------------------------------------------------
REM 6. Open dashboard
REM ------------------------------------------------------------
echo.
echo ============================================================
echo [5/5] OPENING GREENLEDGER DASHBOARD
echo ============================================================

start "" "http://127.0.0.1:8000"

echo.
echo ============================================================
echo                 GREENLEDGER IS RUNNING
echo ============================================================
echo.
echo Module 0:
echo   http://127.0.0.1:8000
echo.
echo Keep the Module 0 terminal window open.
echo Close that window when you want to stop the API.
echo.
echo ============================================================

pause
endlocal
