@echo off
cd /d "%~dp0"
echo ========================================================
echo   AutoApply AI — One-Click Development Launch
echo ========================================================

echo 1. Launching Backend (FastAPI on http://127.0.0.1:8000)...
start "AutoApply AI - Backend" cmd /k "cd /d %~dp0backend && run_backend.bat"

timeout /t 2 /nobreak >nul

echo 2. Launching Next.js Frontend (on http://127.0.0.1:3000)...
start "AutoApply AI - Frontend" cmd /k "cd /d %~dp0frontend && run_frontend.bat"

timeout /t 2 /nobreak >nul

echo 3. Opening AutoApply AI in your default web browser...
start http://127.0.0.1:3000/

echo Done! AutoApply AI is running in the background.
exit /b 0
