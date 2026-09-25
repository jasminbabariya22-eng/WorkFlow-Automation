@echo off
title BPCL Workflow Automation Platform (HTTPS / SSL Enabled)
color 0A

echo ===============================================================================
echo            BPCL Workflow Automation Platform - HTTPS / SSL Server
echo ===============================================================================
echo.

cd /d "%~dp0backend"

if not exist "certs\fullchain.pem" (
    echo [SSL] Generating SSL Certificates for Server IP / Localhost...
    .\.venv\Scripts\python.exe generate_ssl_certs.py
    echo.
)

echo [SERVER] Starting FastAPI Backend on https://0.0.0.0:8000 ...
echo [ACCESS] Swagger Documentation: https://localhost:8000/docs
echo [ACCESS] Server Network Access: https://192.168.1.191:8000/docs
echo ===============================================================================
echo.

.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --ssl-keyfile certs/privkey.pem --ssl-certfile certs/fullchain.pem --reload

pause
