@echo off
title IT ENVANTER SSTEM - ÇALITIRICI
echo Sistem baslatiliyor...

start python main.py
echo Flask Uygulamasi baslatildi (Port 5000).

start python backup_manager.py
echo Otomatik Yedekleme Sistemi baslatildi (15 dk aralikla).

echo.
echo Sistem calisiyor. Kapatmak icin bu pencereyi kapatin.
pause
