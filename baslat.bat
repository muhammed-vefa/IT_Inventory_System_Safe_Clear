@echo off
:: Yonetici yetkilerini kontrol et ve gerekirse iste
net session >nul 2>&1
if %errorLevel% neq 0 (
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

:: Batch dosyasinin bulundugu dizine (klasore) otomatik gecis yap
cd /d "%~dp0"

:: Eger sistem zaten aciksa onceki calisan port 5000 surecini kapat
FOR /F "tokens=5" %%a IN ('netstat -aon ^| find ":5000" ^| find "LISTENING"') DO (
    taskkill /F /PID %%a >nul 2>&1
)
taskkill /F /IM pythonw.exe /FI "WINDOWTITLE eq IT INVENTORY SISTEMI - ANA SUNUCU*" >nul 2>&1

:: Gerekli eklentilerin kurulu oldugundan emin ol
python -m playwright install chromium >nul 2>&1

:: Masaustu arayuzunu (GUI) baslat ve bu siyah ekrani hemen kapat
start "" pythonw tools\gui_launcher.py