@echo off
cd /d "%~dp0"
echo Starting AutoApply AI Next.js Frontend on http://127.0.0.1:3000 ...

:: Check if port 3000 is occupied by a lingering process and free it
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":3000" ^| findstr "LISTENING"') do (
    echo [INFO] Detected lingering process on port 3000 (PID: %%a). Freeing port...
    taskkill /F /PID %%a >nul 2>&1
)

npm run dev
