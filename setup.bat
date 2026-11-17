@echo off
REM GastronomIA - instalación de dependencias (correr UNA vez, y cada tanto para actualizar)
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo === 1/4 Backend (Python) ===
python -m pip install --upgrade pip
python -m pip install -r backend\requirements.txt
if errorlevel 1 (echo ERROR instalando dependencias de Python & pause & exit /b 1)

echo.
echo === 2/4 Frontend (Node) - instala exactamente lo que dice el package-lock.json ===
cd frontend
call npm ci
if errorlevel 1 (echo ERROR en npm ci & pause & exit /b 1)

echo.
echo === 3/4 Actualizando Vite (correcciones de seguridad) ===
call npm update vite
call npm audit
cd ..

echo.
echo === 4/4 Auditoria de Python ===
python -m pip install pip-audit
python -m pip_audit -r backend\requirements.txt

echo.
echo === Listo. Revisa backend\.env: GEMINI_API_KEY tiene que tener tu clave NUEVA. ===
echo Para arrancar todo: restart.bat
pause
