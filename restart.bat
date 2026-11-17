@echo off
title Gastro IA - Restart
echo.
echo ============================================
echo   Restarting Gastro IA...
echo ============================================
echo.

:: Kill existing processes
echo Stopping existing servers...
taskkill /F /FI "WINDOWTITLE eq Gastro IA Backend*" >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq GastroIA Backend*" >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq GastroIA Frontend*" >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq Gastro IA Frontend*" >nul 2>&1
timeout /t 2 /nobreak >nul

:: Find and kill processes on ports 8001 and 5173
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8001 ^| findstr LISTENING') do taskkill /F /PID %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5173 ^| findstr LISTENING') do taskkill /F /PID %%a >nul 2>&1
timeout /t 2 /nobreak >nul

echo Starting servers...
echo.

echo [1/2] Starting Backend on port 8001...
start "GastroIA Backend" cmd /c "cd /d %~dp0 && python run_backend.py"

timeout /t 4 /nobreak >nul

echo [2/2] Starting Frontend on port 5173...
start "GastroIA Frontend" cmd /c "cd /d %~dp0frontend && npm run dev"

echo.
echo ============================================
echo   Servers started!
echo.
echo   Backend:  http://127.0.0.1:8001
echo   API Docs: http://127.0.0.1:8001/docs
echo   Frontend: http://localhost:5173
echo ============================================
echo.
echo Press any key to close this window...
pause >nul
