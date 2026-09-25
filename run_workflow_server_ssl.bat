@echo off
title BPCL Workflow Automation Platform (HTTPS / SSL Enabled)
color 0A

echo ===============================================================================
echo            BPCL Workflow Automation Platform - Full Stack SSL Launch
echo ===============================================================================
echo.

cd /d "%~dp0"

REM 1. SSL Certificate Check & Generation
if not exist "backend\certs\fullchain.pem" (
    echo [SSL] Generating SSL Certificates for Server IP / Localhost...
    cd backend
    .\.venv\Scripts\python.exe generate_ssl_certs.py
    cd ..
    echo.
)

echo ===============================================================================
echo  SERVICES STARTING WITH HTTPS / SSL:
echo  - Workflow Studio UI (HTTPS):   https://192.168.1.191:5173  (or https://localhost:5173)
echo  - Backend API (HTTPS):          https://192.168.1.191:8000  (or https://localhost:8000)
echo  - API Swagger Docs (HTTPS):     https://192.168.1.191:8000/docs
echo ===============================================================================
echo.

REM 2. Launch Backend in background window with SSL
start "Workflow Backend (SSL)" cmd /k "cd /d "%~dp0backend" && .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --ssl-keyfile certs/privkey.pem --ssl-certfile certs/fullchain.pem --reload"

REM 3. Launch Frontend Studio Dashboard in background window with SSL
timeout /t 2 /nobreak >nul
start "Workflow Studio UI (SSL)" cmd /k "cd /d "%~dp0frontend" && npm run dev -- --host 0.0.0.0 --port 5173"

echo [SUCCESS] Both Backend and Frontend Studio Dashboard are running securely with HTTPS!
echo Open your browser at: https://192.168.1.191:5173
echo.
pause
