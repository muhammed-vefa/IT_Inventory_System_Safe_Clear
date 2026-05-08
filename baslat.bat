@echo off
title IT Inventory System - Sunucu
echo ══════════════════════════════════════════════════════
echo        IT INVENTORY SYSTEM BASLATILIYOR
echo ══════════════════════════════════════════════════════
echo.
echo [1/2] Bagimliliklar kontrol ediliyor...
python -m pip install -r requirements.txt --quiet
echo [2/2] Ana uygulama baslatiliyor...
echo.
python main.py
echo.
echo ══════════════════════════════════════════════════════
echo [UYARI] Uygulama kapandi veya bir hata olustu.
pause
