@echo off
title Enterprise Client Portal (Port 3000)
echo ============================================================
echo Starting Enterprise Client Portal on 0.0.0.0:3000
echo ============================================================

cd /d "%~dp0"
npm run dev
pause
