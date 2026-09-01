@echo off
setlocal enabledelayedexpansion
title Enterprise Workflow Platform Server (Port 8000 & 5173)

echo =======================================================================
echo          ENTERPRISE WORKFLOW PLATFORM - AUTO DEPLOYMENT
echo =======================================================================

cd /d "%~dp0"

REM ---------------------------------------------------------
REM 1. PREREQUISITE CHECKS (Python & Node.js)
REM ---------------------------------------------------------
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH!
    echo Please install Python 3.10+ from https://www.python.org/downloads/
    echo (Make sure to check 'Add Python to PATH' during installation)
    pause
    exit /b 1
)

npm --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js / NPM is not installed or not in PATH!
    echo Please install Node.js 18+ from https://nodejs.org/
    pause
    exit /b 1
)

REM ---------------------------------------------------------
REM 2. AUTO-INSTALL BACKEND DEPENDENCIES IF MISSING
REM ---------------------------------------------------------
if not exist "backend\.venv\Scripts\python.exe" (
    echo [INFO] Python virtual environment not found. Setting up backend...
    echo [1/2] Creating virtual environment (.venv)...
    python -m venv backend\.venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment!
        pause
        exit /b 1
    )
    echo [2/2] Installing required Python packages from requirements.txt...
    call backend\.venv\Scripts\activate.bat
    python -m pip install --upgrade pip
    pip install -r backend\requirements.txt
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install backend dependencies!
        pause
        exit /b 1
    )
    echo [SUCCESS] Backend dependencies installed successfully!
) else (
    echo [OK] Backend virtual environment verified.
)

REM ---------------------------------------------------------
REM 3. AUTO-INSTALL FRONTEND DEPENDENCIES IF MISSING
REM ---------------------------------------------------------
if not exist "frontend\node_modules\" (
    echo.
    echo [INFO] Frontend dependencies not found. Installing node_modules...
    cd frontend
    call npm install
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install frontend node_modules!
        cd ..
        pause
        exit /b 1
    )
    cd ..
    echo [SUCCESS] Frontend dependencies installed successfully!
) else (
    echo [OK] Frontend node_modules verified.
)

REM ---------------------------------------------------------
REM 4. DETECT LOCAL NETWORK IP ADDRESS
REM ---------------------------------------------------------
set LOCAL_IP=127.0.0.1
for /f "tokens=4" %%a in ('route print ^| findstr 0.0.0.0 ^| findstr /v "127.0.0.1"') do (
    set LOCAL_IP=%%a
)

echo.
echo =======================================================================
echo  SERVICES READY TO LAUNCH ON ALL NETWORK INTERFACES (0.0.0.0)
echo =======================================================================
echo  - Workflow Studio UI:   http://localhost:5173  (Network: http://%LOCAL_IP%:5173)
echo  - Workflow Engine API:  http://localhost:8000  (Network: http://%LOCAL_IP%:8000)
echo  - API Swagger Docs:     http://localhost:8000/docs
echo =======================================================================
echo.

REM ---------------------------------------------------------
REM 5. LAUNCH SERVICES IN PARALLEL
REM ---------------------------------------------------------
echo Starting Backend API Server on 0.0.0.0:8000...
start "Workflow Engine Backend" cmd /k "cd /d "%~dp0backend" && call .venv\Scripts\activate.bat && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

timeout /t 2 /nobreak >nul

echo Starting Frontend Studio UI on 0.0.0.0:5173...
start "Workflow Studio Frontend" cmd /k "cd /d "%~dp0frontend" && npm run dev -- --host 0.0.0.0 --port 5173"

echo.
echo [DONE] Both services are running in their respective terminal windows!
echo You can now access the platform from any browser on your network.
echo.
pause
