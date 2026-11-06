@echo off
chcp 65001 > nul
title IT INVENTORY - MYM KULLANICILARI VE SİCİL NO ÇEKME ARACI
cls

echo =====================================================================
echo       IT INVENTORY - MYM KULLANICI VE SİCİL NO ÇEKME ARACI
echo =====================================================================
echo.
echo Bu araç mym.kocaelish.com sistemine bağlanarak güncel kullanıcıları
echo çeker, personel havuzunu ve VPN kullanıcılarının sicil numaralarını
echo otomatik olarak veritabanına işler.
echo.

:: -----------------------------------------------------------------------
:: İSTERSENİZ KULLANICI ADI VE ŞİFRENİZİ AŞAĞIYA SABİT OLARAK YAZABİLİRSİNİZ:
:: (Eğer buraya yazarsanız her seferinde sormaz, otomatik çalışır)
:: -----------------------------------------------------------------------
set "MYM_KULLANICI="
set "MYM_SIFRE="

:: Eğer yukarıda tanımlanmamışsa kullanıcıya sor
if "%MYM_KULLANICI%"=="" (
    set /p "MYM_KULLANICI=MYM Kullanıcı Adı : "
)
if "%MYM_SIFRE%"=="" (
    set /p "MYM_SIFRE=MYM Şifresi       : "
)

if "%MYM_KULLANICI%"=="" (
    echo [HATA] Kullanıcı adı boş bırakılamaz!
    pause
    exit /b 1
)

echo.
echo [1] Gizli Mod (Arka planda sessiz çalıştır - Önerilen)
echo [2] Görsel Mod (Tarayıcıyı ekranda görerek çalıştır)
echo.
set /p "MOD_SECIM=Seçiminiz [1 veya 2] (Varsayılan 1): "

set "PARAM_HEADED="
if "%MOD_SECIM%"=="2" (
    set "PARAM_HEADED=--headed"
)

echo.
echo [*] İşlem başlatılıyor, lütfen bekleyin...
echo.

cd /d "%~dp0"
python mym_kullanici_cek.py --user "%MYM_KULLANICI%" --pass "%MYM_SIFRE%" %PARAM_HEADED%

if %errorlevel% neq 0 (
    echo.
    echo [!] Bir hata oluştu. Lütfen bilgilerinizi veya internet bağlantınızı kontrol edin.
)

echo.
pause
