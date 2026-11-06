@echo off
title IT INVENTORY - VPN VERILERINI YUKLE
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Yonetici yetkileri aliniyor...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)
cd /d "%~dp0"

echo ===================================================
echo     IT INVENTORY - VPN VERILERI AKTARIM ARACI
echo ===================================================
echo.

if exist "import_vpn_excel.py" (
    python import_vpn_excel.py
) else if exist "..\tools\import_vpn_excel.py" (
    python ..\tools\import_vpn_excel.py
) else if exist "tools\import_vpn_excel.py" (
    python tools\import_vpn_excel.py
) else (
    echo [HATA] import_vpn_excel.py dosyasi bulunamadi!
    pause
)
