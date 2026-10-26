@echo off
chcp 65001 >nul
set "MK=%LOCALAPPDATA%\MarketKiyas"
echo MarketKıyas kapatılıyor...
taskkill /FI "WINDOWTITLE eq MK-WEB*" /T /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq MK-WORKER*" /T /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq MK-API*" /T /F >nul 2>&1
"%MK%\pgsql\bin\pg_ctl.exe" -D "%MK%\data" stop -m fast >nul 2>&1
echo Kapatıldı.
timeout /t 3 >nul
