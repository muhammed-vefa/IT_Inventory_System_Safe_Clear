@echo off
title IT INVENTORY - VERITABANI VERI YONETIM ARACI
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Yonetici yetkileri aliniyor...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)
cd /d "%~dp0"

:menu
cls
echo ===================================================
echo       IT INVENTORY - VERITABANI VERI YONETIMI
echo ===================================================
echo.
echo   [1] Verileri Temizle (Tum tablolari bosalt)
echo   [2] Excel'den Veritabanina Veri Yukle
echo   [3] SQL Veritabanini Excel'e Aktar (Export)
echo   [4] Cikis
echo.
echo ===================================================
set /p secim="Yapmak istediginiz islemi secin (1/2/3/4): "

if "%secim%"=="1" goto temizle
if "%secim%"=="2" goto yukle
if "%secim%"=="3" goto export
if "%secim%"=="4" goto cikis
echo [!] Gecersiz secim. Tekrar deneyin.
timeout /t 2 >nul
goto menu

:temizle
echo.
echo ===================================================
echo    DIKKAT: TUM VERILER SILINECEKTIR!
echo    (Envanter, Yazicilar, Servis Kayitlari,
echo     Kullanicilar, Loglar vb.)
echo ===================================================
echo.
set /p onay="Devam etmek istediginizden emin misiniz? (E/H): "
if /i "%onay%" neq "E" (
    echo [!] Temizleme islemi iptal edildi.
    timeout /t 2 >nul
    goto menu
)

echo.
echo [*] Veritabanina baglaniliyor...
python tools/sql_excel_verileri_temizle.py --force
echo.

echo ===================================================
echo    Temizleme islemi tamamlandi!
echo ===================================================
echo.
set /p yukle_onay="Simdi Excel'den verileri yuklemek ister misiniz? (E/H): "
if /i "%yukle_onay%"=="E" goto yukle

echo.
pause
goto menu

:yukle
echo.
echo ===================================================
echo    EXCEL'DEN VERITABANINA VERI YUKLEME
echo ===================================================
echo.
echo [*] database/ klasorundeki Excel dosyalari okunacak
echo     ve SQL Server'a aktarilacak.
echo.
python tools/excel_verileri_yukle.py
echo.
echo ===================================================
echo    VERI YUKLEME ISLEMI TAMAMLANDI!
echo ===================================================
echo.
pause
goto menu

:export
echo.
echo ===================================================
echo    SQL VERITABANINI EXCEL'E AKTARMA (EXPORT)
echo ===================================================
echo.
echo [*] Gerekli paketler kontrol ediliyor (pandas, openpyxl)...
pip install pandas openpyxl >nul 2>&1
echo.
echo [*] Veriler Excel formatinda disari aktariliyor...
python tools/export_sql.py
echo.
echo ===================================================
echo    ISLEM TAMAMLANDI!
echo ===================================================
echo.
pause
goto menu

:cikis
echo.
echo Cikis yapiliyor...
exit
