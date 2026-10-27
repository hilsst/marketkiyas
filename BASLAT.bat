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
rem Tarayıcı API'ye arayüz üzerinden ulaşır (next.config.js); telefon da aynı adresi kullanabilir
set "NEXT_PUBLIC_API_URL=/api"
rem Hızlı mod: kod değiştiyse (ya da hiç derlenmediyse) bir kez derlenir, sonra hazır sayfalar sunulur
for /f %%h in ('git -C "%~dp0." rev-parse HEAD 2^>nul') do set "HEAD=%%h"
set "BUILT="
if exist ".next\marketkiyas-head.txt" set /p BUILT=<".next\marketkiyas-head.txt"
if not exist ".next\BUILD_ID" set "BUILT="
if not "%BUILT%"=="%HEAD%" (
  echo Uygulama güncellendiği için hazırlanıyor, bu bir-iki dakika sürebilir...
  call npm run build > "%MK%\build.log" 2>&1 || (
    echo !!! Hazırlama başarısız oldu. %MK%\build.log dosyasını Claude'a gönderin.
    pause
    exit /b 1
  )
  >".next\marketkiyas-head.txt" echo %HEAD%
)
start "MK-WEB" /min cmd /c "npm run start -- -H 0.0.0.0 -p 3000 > "%MK%\web.log" 2>&1"

timeout /t 5 /nobreak >nul
start "" http://localhost:3000
echo.
echo Uygulama tarayıcıda açıldı: http://localhost:3000
echo Aynı Wi-Fi'deki telefondan açmak için tarayıcıya şu adreslerden birini yazın:
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do for /f "tokens=*" %%b in ("%%a") do echo    http://%%b:3000
echo (Windows güvenlik duvarı sorarsa "Özel ağlar"a izin verin.)
echo Kapatmak için DURDUR dosyasına çift tıklayın.
timeout /t 30 >nul
