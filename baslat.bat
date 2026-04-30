@echo off
setlocal
title IT Inventory System - Baslatiliyor
cd /d %~dp0
echo ======================================================
echo       IT INVENTORY SYSTEM - BASLATILIYOR
echo ======================================================

:: Python kontrolu
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [HATA] Python bulunamadi! 
    echo Lutfen Python'un yuklu oldugundan ve PATH'e eklendiginden emin olun.
    pause
    exit /b
)

:: Gerekli kutuphaneleri kontrol et ve yukle
echo [1/2] Bagimliliklar kontrol ediliyor...
python -m pip install --upgrade pip
python -m pip install flask flask-cors pyodbc openpyxl werkzeug requests

:: Uygulamayi baslat
echo [2/2] Uygulama baslatiliyor...
timeout /t 2 >nul
python main.py
if %errorlevel% neq 0 (
    echo [HATA] Uygulama beklenmedik bir sekilde kapandi.
    pause
)
pause