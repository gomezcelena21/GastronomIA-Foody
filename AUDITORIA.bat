@echo off
REM GastronomIA - AUDITORIA AUTOMATICA (doble clic)
chcp 65001 >nul
title GastronomIA - Auditoria automatica
cd /d "%~dp0"
echo ============================================================
echo   GastronomIA - Auditoria automatica
echo   Revisa el codigo, corre las pruebas y arma el reporte
echo ============================================================
echo.
python auditoria\auditar.py
echo.
if exist auditoria\reporte\reporte_auditoria.html (
  echo Abriendo el reporte en el navegador...
  start "" auditoria\reporte\reporte_auditoria.html
)
pause
