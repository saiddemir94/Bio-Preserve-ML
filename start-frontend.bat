@echo off
setlocal

cd /d "%~dp0frontend"

if not exist "node_modules" (
  echo Frontend bagimliliklari bulunamadi. Once setup.bat calistirin.
  pause
  exit /b 1
)

call npm.cmd run dev
pause
