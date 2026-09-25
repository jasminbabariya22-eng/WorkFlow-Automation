@echo off
title BPCL Workflow Automation - Docker Production Deployment with SSL
color 0B

echo ===============================================================================
echo       BPCL Workflow Automation Platform - Docker Production Deployment (SSL)
echo ===============================================================================
echo.

:: 1. Verify Docker is running
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker is not running! Please start Docker Desktop or Docker Engine first.
    pause
    exit /b 1
)

:: 2. Ensure SSL Certificates exist
cd /d "%~dp0"
if not exist "backend\certs\fullchain.pem" (
    echo [SSL] Generating SSL Certificates for HTTPS / Port 443...
    if exist "backend\.venv\Scripts\python.exe" (
        backend\.venv\Scripts\python.exe backend\generate_ssl_certs.py
    ) else (
        python backend\generate_ssl_certs.py
    )
    echo.
)

:: 3. Backup previous running state tag for instant rollback
echo [DEPLOY] Tagging previous stable deployment for rollback safety...
docker compose ps -q > .last_deployment_state.txt 2>nul

:: 4. Build and Deploy Full Stack with SSL
echo [DEPLOY] Building and starting all Docker containers (Backend + Frontend SSL + Dashboards)...
docker compose up -d --build --remove-orphans

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Deployment failed! Run 'docker_rollback.bat' to restore previous state.
    pause
    exit /b 1
)

echo.
echo ===============================================================================
echo                        DEPLOYMENT SUCCESSFUL!
echo ===============================================================================
echo [STATUS] Application is running securely with SSL (HTTPS)
echo.
echo  - Workflow Studio UI (HTTPS):    https://192.168.1.191  (or https://localhost)
echo  - Workflow Studio UI (HTTP):     http://192.168.1.191   (or http://localhost)
echo  - Backend API Swagger Docs:      http://192.168.1.191:8000/docs
echo  - Grafana Observability Portal:  http://192.168.1.191:3001
echo.
echo  To view live logs:    docker compose logs -f
echo  To rollback / stop:   docker_rollback.bat
echo ===============================================================================
echo.
pause
