@echo off
title Gastro IA - Full Stack
echo.
echo ============================================
echo   GASTRO IA - Starting All Services
echo ============================================
echo.

echo [1/2] Starting Backend on port 8001...
start "GastroIA Backend" cmd /c "cd /d %~dp0 && python run_backend.py"

timeout /t 4 /nobreak >nul

echo [2/2] Starting Frontend on port 5173...
start "GastroIA Frontend" cmd /c "cd /d %~dp0frontend && npm run dev"

echo.
echo ============================================
echo   Both services starting...
echo.
echo   Backend:  http://127.0.0.1:8001
echo   API Docs: http://127.0.0.1:8001/docs
echo   Frontend: http://localhost:5173
echo ============================================
echo.
echo Close this window or press Ctrl+C to stop.
pause
