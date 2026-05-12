@echo off
title IT ENVANTER SİSTEMİ - ANA SUNUCU
echo ===================================================
echo   KEYDATA IT ENVANTER SISTEMI BASLATILIYOR
echo ===================================================
echo.

:: 1. Yedekleme Sistemini Gizli/Kucuk Pencerede Baslat
echo [+] Otomatik Yedekleme Servisi baslatiliyor...
start "IT_YEDEKLEME" /min python backup_manager.py

:: 2. Tarayiciyi birazdan acilacak sekilde ayarla
echo [+] Web Arayuzu hazirlaniyor...
timeout /t 2 >nul
start http://localhost:5000

:: 3. Ana Uygulamayi (Flask) bu pencerede baslat
echo [+] Flask Sunucusu (Port 5000) AKTIF ediliyor...
echo [!] Bu pencereyi kapatirsaniz site erisime kapanir.
echo.
python main.py

pause
