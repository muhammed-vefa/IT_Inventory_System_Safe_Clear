@echo off
setlocal enabledelayedexpansion
title KEYDATA KOCAELİ - SİSTEM SIFIRLAMA
chcp 65001 > nul

echo.
echo ══════════════════════════════════════════════════════
echo   DİKKAT: TÜM VERİLER VE DOSYALAR SİLİNECEKTİR!
echo ══════════════════════════════════════════════════════
echo.
echo [1] Veritabanı tabloları sıfırlanacak (Locations, Inventory, Service, vb.)
echo [2] Yüklenmiş tüm resimler ve dosyalar silinecek.
echo [3] Log dosyaları temizlenecek.
echo.
set /p onay="Devam etmek için 'EVET' yazın: "

if /i "!onay!" neq "EVET" (
    echo.
    echo İptal edildi.
    pause
    exit
)

echo.
echo [!] Sistem sıfırlanıyor, lütfen bekleyin...

:: 1. Veritabanını Sıfırla (Python scripti üzerinden güvenli temizlik)
set PYTHONPATH=.
python -c "from core.database_sql import get_db_connection; conn=get_db_connection(); tables=['locations','inventory','printers','printer_service','warehouse','shared_areas']; [conn.execute(f'DELETE FROM {t}') for t in tables]; conn.commit(); conn.close(); print('Veritabanı tabloları başarıyla sıfırlandı.')"

:: 2. Yüklenen dosyaları temizle (uploads klasörü)
if exist uploads (
    echo [+] Yüklenen dosyalar temizleniyor...
    del /q uploads\* > nul 2>&1
    for /d %%x in (uploads\*) do rd /s /q "%%x"
)

:: 3. Logları temizle
if exist logs (
    echo [+] Log dosyaları temizleniyor...
    del /q logs\* > nul 2>&1
)

:: 4. Geçici dosyaları temizle
if exist __pycache__ rd /s /q __pycache__
if exist core\__pycache__ rd /s /q core\__pycache__
if exist modules\__pycache__ rd /s /q modules\__pycache__

echo.
echo ══════════════════════════════════════════════════════
echo   SİSTEM BAŞARIYLA SIFIRLANDI!
echo ══════════════════════════════════════════════════════
echo.
echo Artık yeni Excel dosyalarınızla senkronizasyon yapabilirsiniz.
pause
