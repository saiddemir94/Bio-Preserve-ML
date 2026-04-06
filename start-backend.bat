@echo off
setlocal

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Sanal ortam bulunamadi. Once setup.bat calistirin.
  pause
  exit /b 1
)

call ".venv\Scripts\python.exe" -m uvicorn backend.main:app --reload
pause
