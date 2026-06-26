@echo off
title IT Inventory - GITHUB MANUEL YEDEK YUKLEME
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Yonetici yetkileri aliniyor...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)
cd /d "%~dp0"
echo ===================================================
echo    IT INVENTORY - GITHUB MANUEL YEDEK YUKLEME
echo ===================================================
echo.
echo [*] Degisiklikler taraniyor...
git status
echo.
set /p onay="Bu degisiklikleri GitHub'a manuel yuklemek istiyor musunuz? (E/H): "
if /i "%onay%" neq "E" goto iptal

echo.
echo [*] Dosyalar yedekleme listesine ekleniyor...
git add .

set /p commit_msg="Lutfen yedekleme notu girin (Bos birakmak icin Enter): "
if "%commit_msg%"=="" set commit_msg="Manuel Yedekleme"

echo [*] Yedek paketi olusturuluyor...
git commit -m "%commit_msg%"

echo [*] GitHub'a yukleniyor (Push)...
git push origin staging-safe-release

echo.
echo ===================================================
echo    Yedekleme basariyla tamamlandi!
echo ===================================================
pause
exit

:iptal
echo.
echo [!] Islem iptal edildi.
pause
exit