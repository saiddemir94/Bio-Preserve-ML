@echo off
setlocal

cd /d "%~dp0"

where py >nul 2>nul
if errorlevel 1 (
  echo Python launcher ^(py^) bulunamadi. Lutfen Python 3.12 kurun.
  pause
  exit /b 1
)

where npm.cmd >nul 2>nul
if errorlevel 1 (
  echo npm bulunamadi. Lutfen Node.js kurun.
  pause
  exit /b 1
)

py -3.12 -m venv .venv
if errorlevel 1 (
  echo Python 3.12 ile sanal ortam olusturulamadi.
  pause
  exit /b 1
)

call ".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 (
  echo pip guncellenemedi.
  pause
  exit /b 1
)

call ".venv\Scripts\python.exe" -m pip install -r backend\requirements.txt
if errorlevel 1 (
  echo Backend bagimliliklari kurulurken hata olustu.
  pause
  exit /b 1
)

call ".venv\Scripts\python.exe" ml\train_model.py
if errorlevel 1 (
  echo Model egitimi sirasinda hata olustu.
  pause
  exit /b 1
)

cd /d "%~dp0frontend"
call npm.cmd install
if errorlevel 1 (
  echo Frontend bagimliliklari kurulurken hata olustu.
  pause
  exit /b 1
)

echo Kurulum tamamlandi.
pause
