@echo off
title BPCL Workflow Automation Platform (HTTPS / SSL Enabled)
color 0A

echo ===============================================================================
echo            BPCL Workflow Automation Platform - Full Stack SSL Launch
echo ===============================================================================
echo.

cd /d "%~dp0"

REM Detect Python interpreter (prefer project venv if present, otherwise system PATH)
set "PYTHON_CMD=python"
if exist "%~dp0backend\.venv\Scripts\python.exe" (
    set "PYTHON_CMD=%~dp0backend\.venv\Scripts\python.exe"
)

REM 1. SSL Certificate Check & Generation
if not exist "backend\certs\fullchain.pem" (
    echo [SSL] Generating SSL Certificates for Server IP / Localhost...
    cd backend
    "%PYTHON_CMD%" generate_ssl_certs.py
    cd ..
    echo.
)

REM 2. Resolve Configured Host from Environment
set "CONFIGURED_HOST=localhost"
if exist "backend\.env" (
    for /f "usebackq tokens=1,2 delims==" %%A in ("backend\.env") do (
        if /i "%%A"=="MAIN_URL" (
            for /f "tokens=2 delims=/" %%C in ("%%B") do (
                for /f "tokens=1 delims=:" %%D in ("%%C") do (
                    set "CONFIGURED_HOST=%%D"
                )
            )
        )
    )
)

echo ===============================================================================
echo  SERVICES STARTING WITH HTTPS / SSL:
echo  - Workflow Studio UI (HTTPS):   https://%CONFIGURED_HOST%:5173  (or https://localhost:5173)
echo  - Backend API (HTTPS):          https://%CONFIGURED_HOST%:8000  (or https://localhost:8000)
echo  - API Swagger Docs (HTTPS):     https://%CONFIGURED_HOST%:8000/docs
echo ===============================================================================
echo.

REM 3. Launch Backend in background window with SSL
start "Workflow Backend (SSL)" cmd /k "cd /d "%~dp0backend" && "%PYTHON_CMD%" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --ssl-keyfile certs/privkey.pem --ssl-certfile certs/fullchain.pem --reload"

REM 4. Launch Frontend Studio Dashboard in background window with SSL
timeout /t 2 /nobreak >nul
start "Workflow Studio UI (SSL)" cmd /k "cd /d "%~dp0frontend" && npm run dev -- --host 0.0.0.0 --port 5173"

echo [SUCCESS] Both Backend and Frontend Studio Dashboard are running securely with HTTPS!
echo Opening your browser at: https://%CONFIGURED_HOST%:5173
start https://%CONFIGURED_HOST%:5173
echo.
pause
