@echo off
title Enterprise Workflow Server (Port 8000 & 5173)
echo ============================================================
echo Starting Enterprise Workflow Server on 0.0.0.0 (Accessible Anywhere)
echo ============================================================

REM Find local network IP
for /f "tokens=4" %%a in ('route print ^| findstr 0.0.0.0 ^| findstr /v "127.0.0.1"') do set LOCAL_IP=%%a

echo Workflow API Backend: http://0.0.0.0:8000 (LAN: http://%LOCAL_IP%:8000)
echo Workflow Studio UI:   http://0.0.0.0:5173 (LAN: http://%LOCAL_IP%:5173)
echo ============================================================

cd /d "%~dp0"

REM 1. Start Backend in new window
start "Workflow Engine Backend" cmd /k "cd backend && call .venv\Scripts\activate.bat && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

REM 2. Start Frontend Studio in new window
start "Workflow Studio Frontend" cmd /k "cd frontend && npm run dev -- --host 0.0.0.0 --port 5173"

echo Both services launched successfully!
pause
