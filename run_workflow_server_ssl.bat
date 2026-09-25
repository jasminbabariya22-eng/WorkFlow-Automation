@echo off
title BPCL Workflow Automation Platform (HTTPS / SSL Enabled)
color 0A

echo ===============================================================================
echo            BPCL Workflow Automation Platform - Full Stack Launch
echo ===============================================================================
echo.

cd /d "%~dp0"

REM 1. SSL Certificate Check
if not exist "backend\certs\fullchain.pem" (
    echo [SSL] Generating SSL Certificates for Server IP / Localhost...
    cd backend
    .\.venv\Scripts\python.exe generate_ssl_certs.py
    cd ..
    echo.
)

echo ===============================================================================
echo  SERVICES STARTING:
echo  - Workflow Studio UI:        http://192.168.1.191:5173  (or http://localhost:5173)
echo  - Backend API (HTTPS/SSL):   https://192.168.1.191:8000 (or https://localhost:8000)
echo  - API Swagger Documentation: https://192.168.1.191:8000/docs
echo ===============================================================================
echo.

REM 2. Launch Backend in background window
start "Workflow Backend (SSL)" cmd /k "cd /d "%~dp0backend" && .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --ssl-keyfile certs/privkey.pem --ssl-certfile certs/fullchain.pem --reload"

REM 3. Launch Frontend Dashboard UI
timeout /t 2 /nobreak >nul
start "Workflow Studio UI" cmd /k "cd /d "%~dp0frontend" && npm run dev -- --host 0.0.0.0 --port 5173"

echo [SUCCESS] Both Backend (SSL) and Frontend Studio Dashboard are running!
echo Open your browser at: http://192.168.1.191:5173
echo.
pause
