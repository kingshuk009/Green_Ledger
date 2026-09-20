@echo off
for /f "tokens=5" %%P in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do taskkill /PID %%P /T /F >nul 2>&1
for /f "tokens=2" %%P in ('tasklist ^| findstr /I "module1.py"') do taskkill /PID %%P /T /F >nul 2>&1
 echo GreenLedger services stopped.
 pause
