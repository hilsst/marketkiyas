@echo off
chcp 65001 >nul
setlocal
title MarketKiyas kurulum
cd /d "%~dp0"
set "MK=%LOCALAPPDATA%\MarketKiyas"
set "PG=%MK%\pgsql\bin"
set "PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if not exist "%MK%" mkdir "%MK%"

echo.
echo === MarketKıyas kurulumu (bir kez yapılır, 5-10 dakika sürebilir) ===
echo.

echo [1/6] Python kontrol ediliyor...
if not exist "%PY%" (
  winget install -e --id Python.Python.3.12 --scope user --silent --accept-package-agreements --accept-source-agreements || goto hata
)

echo [2/6] Veritabanı programı hazırlanıyor...
if not exist "%PG%\pg_ctl.exe" (
  curl -L -o "%MK%\pg.zip" https://get.enterprisedb.com/postgresql/postgresql-16.10-1-windows-x64-binaries.zip || goto hata
  tar -xf "%MK%\pg.zip" -C "%MK%" --exclude "pgsql/pgAdmin 4" --exclude "pgsql/StackBuilder" --exclude "pgsql/doc" || goto hata
  del "%MK%\pg.zip"
)

echo [3/6] Veritabanı oluşturuluyor...
if not exist "%MK%\data\PG_VERSION" (
  "%PG%\initdb.exe" -D "%MK%\data" -U marketkiyas -A trust -E UTF8 --locale=en-US >"%MK%\initdb.log" 2>&1 || goto hata
)
"%PG%\pg_ctl.exe" -D "%MK%\data" status >nul 2>&1 || "%PG%\pg_ctl.exe" -D "%MK%\data" -l "%MK%\postgres.log" -o "-p 5432 -h localhost" -w start >nul || goto hata
"%PG%\psql.exe" -h localhost -U marketkiyas -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='marketkiyas'" | findstr 1 >nul || "%PG%\createdb.exe" -h localhost -U marketkiyas marketkiyas || goto hata

echo [4/6] Uygulama sunucusu kuruluyor...
cd /d "%~dp0backend"
if not exist ".venv\Scripts\python.exe" ( "%PY%" -m venv .venv || goto hata )
".venv\Scripts\python.exe" -m pip install -q --disable-pip-version-check -r requirements.txt || goto hata
".venv\Scripts\alembic.exe" upgrade head || goto hata

echo [5/6] Örnek ürünler ve listeler yükleniyor...
".venv\Scripts\python.exe" -m app.cli seed-demo || echo (Örnek veriler zaten yüklü olabilir, devam ediliyor)

echo [6/6] Arayüz kuruluyor...
cd /d "%~dp0frontend"
if not exist ".env.local" copy .env.example .env.local >nul
call npm ci --no-audit --no-fund || goto hata

echo.
echo === Kurulum tamam! Şimdi BASLAT dosyasına çift tıklayın. ===
echo.
pause
exit /b 0

:hata
echo.
echo !!! Bir hata oldu. Bu pencerenin ekran görüntüsünü Claude'a gönderin.
echo.
pause
exit /b 1
