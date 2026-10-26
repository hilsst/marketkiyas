@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
set "MK=%LOCALAPPDATA%\MarketKiyas"
set "PG=%MK%\pgsql\bin"

if not exist "%~dp0backend\.venv\Scripts\python.exe" (
  echo Önce 1-KUR dosyasına çift tıklayıp kurulumu yapın.
  pause
  exit /b 1
)

echo MarketKıyas açılıyor...
"%PG%\pg_ctl.exe" -D "%MK%\data" status >nul 2>&1 || "%PG%\pg_ctl.exe" -D "%MK%\data" -l "%MK%\postgres.log" -o "-p 5432 -h localhost" -w start >nul

cd /d "%~dp0backend"
".venv\Scripts\alembic.exe" upgrade head >nul 2>&1
start "MK-API" /min cmd /c ".venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 > "%MK%\api.log" 2>&1"
rem marketfiyati.org.tr'den seçili şubelerin fiyatlarını 6 saatte bir günceller
start "MK-WORKER" /min cmd /c ".venv\Scripts\python.exe -m app.cli sync-selected --every-hours 6 > "%MK%\worker.log" 2>&1"

cd /d "%~dp0frontend"
start "MK-WEB" /min cmd /c "npm run dev > "%MK%\web.log" 2>&1"

echo Birkaç saniye bekleniyor...
timeout /t 15 /nobreak >nul
start "" http://localhost:3000
echo.
echo Uygulama tarayıcıda açıldı: http://localhost:3000
echo Sayfa ilk açılışta yarım dakika kadar yüklenebilir.
echo Kapatmak için DURDUR dosyasına çift tıklayın.
timeout /t 10 >nul
