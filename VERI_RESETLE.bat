@echo off
setlocal
title IT Inventory - Veritabani Sifirlama ve Senkronizasyon
cd /d %~dp0

echo ======================================================
echo    VERITABANI SIFIRLAMA VE EXCEL AKTARIMI (TEK SEFERLIK)
echo ======================================================
echo.
echo DIKKAT: Bu islem mevcut veritabani verilerini (envanter, yazicilar, vb.)
echo tamamen silecek ve Excel dosyalarindaki verileri bastan yukleyecektir.
echo.
set /p onay="Devam etmek istiyor musunuz? (E/H): "
if /i "%onay%" neq "E" goto iptal

echo.
echo [1/2] Veriler temizleniyor ve Excel'den aktariliyor...
python reset_db.py

echo.
echo [2/2] Temizlik islemi yapiliyor...
if exist reset_db.py del reset_db.py

echo.
echo ======================================================
echo ISLEM TAMAMLANDI! 
echo Bu dosya simdi kendini silecektir.
echo ======================================================
pause

:: Kendini silme komutu
(goto) 2>nul & del "%~f0"
exit

:iptal
echo Islem iptal edildi.
pause
exit
