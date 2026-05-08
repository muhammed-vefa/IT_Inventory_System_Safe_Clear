@echo off
title IT Inventory - MANUEL GÜNCELLEME
echo ══════════════════════════════════════════════════════
echo        SİSTEM GÜNCELLEMESİ BAŞLATILIYOR
echo ══════════════════════════════════════════════════════
echo.

echo [1/2] GitHub'dan kodlar kontrol ediliyor...
git fetch origin main
for /f "tokens=*" %%i in ('git pull origin main') do set "GIT_OUT=%%i"

echo %GIT_OUT% | findstr /C:"Already up to date" >nul
if %errorlevel% equ 0 (
    echo.
    echo [BILGI] Kodlar zaten güncel. Yeniden başlatmaya gerek yok.
    echo.
    timeout /t 3
    exit
)

echo.
echo [2/2] Yeni kodlar bulundu! Sistem yeniden başlatılıyor...
taskkill /F /FI "WINDOWTITLE eq IT Inventory System - Sunucu*" /T 2>nul
start baslat.bat

echo.
echo ══════════════════════════════════════════════════════
echo        GÜNCELLEME TAMAMLANDI!
echo ══════════════════════════════════════════════════════
echo.
timeout /t 5
exit
