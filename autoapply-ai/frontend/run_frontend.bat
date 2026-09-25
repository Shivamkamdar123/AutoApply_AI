@echo off
cd /d "%~dp0"
echo Starting AutoApply AI Frontend Dev Server on http://127.0.0.1:5500 ...
python server.py 5500 127.0.0.1
pause
