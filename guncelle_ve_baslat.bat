@echo off
title SISTEM GUNCELLEME VE YENIDEN BASLATMA
cd /d "%~dp0"

echo ===================================================
echo IT INVENTORY GUNCELLEME ARACI
echo ===================================================
echo.
echo Tarayiciya basari mesajinin iletilmesi icin 3 saniye bekleniyor...
timeout /t 3 /nobreak >nul

echo.
echo Sadece Port 5000'i kullanan uygulama (Sistem) sonlandiriliyor...

:: Port 5000'i dinleyen islem (PID) bulunup kapatilir
FOR /F "tokens=5" %%a IN ('netstat -aon ^| find ":5000" ^| find "LISTENING"') DO (
    taskkill /F /PID %%a >nul 2>&1
)
:: IT Inventory cmd penceresini kapat (Eger aciksa)
taskkill /F /IM cmd.exe /FI "WINDOWTITLE eq *IT INVENTORY SISTEMI*" /T >nul 2>&1

echo.
echo Githup uzerinden en guncel dosyalar indiriliyor...
git pull origin main

echo.
echo Sistem yeniden baslatiliyor...
call baslat.bat

exit
