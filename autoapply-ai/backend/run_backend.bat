@echo off
cd /d "%~dp0"
echo ========================================================
echo   AutoApply AI — Starting Backend FastAPI Service
echo ========================================================

if not exist ".env" (
    echo [.env] not found, copying from .env.example ...
    copy .env.example .env >nul
)

if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else (
    echo [WARNING] venv not found. Using system python...
)

echo Starting FastAPI backend at http://127.0.0.1:8000 ...
echo API Documentation available at http://127.0.0.1:8000/docs
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
pause
