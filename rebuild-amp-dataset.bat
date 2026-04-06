@echo off
setlocal

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Sanal ortam bulunamadi. Once setup.bat calistirin.
  pause
  exit /b 1
)

call ".venv\Scripts\python.exe" data_ingestion\build_amp_dataset.py
if errorlevel 1 (
  echo AMP dataset olusturulurken hata olustu.
  pause
  exit /b 1
)

call ".venv\Scripts\python.exe" ml\train_model.py
if errorlevel 1 (
  echo Model egitilirken hata olustu.
  pause
  exit /b 1
)

echo AMP dataset guncellendi ve model yeniden egitildi.
pause
