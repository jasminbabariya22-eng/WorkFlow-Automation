@echo off
title BPCL Workflow Automation - Rollback / Revoke Deployment
color 0C

echo ===============================================================================
echo       BPCL Workflow Automation Platform - Rollback / Revoke Deployment
echo ===============================================================================
echo.

cd /d "%~dp0"

echo [ROLLBACK] Stopping all current Docker containers and revoking deployment...
docker compose down

echo.
echo [STATUS] Deployment has been revoked and all containers are cleanly stopped.
echo.
echo If you want to redeploy, run:  docker_deploy.bat
echo ===============================================================================
echo.
pause
