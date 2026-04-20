@echo off
setlocal
cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
    echo [run.bat] venv not found. Please create it first:
    echo     python -m venv venv
    echo     venv\Scripts\pip install -r requirements.txt
    exit /b 1
)

"venv\Scripts\python.exe" main.py %*
endlocal
