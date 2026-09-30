@echo off
:: Yonetici (Admin) Kontrolu
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] HATA: Bu islem yonetici (Administrator) haklari gerektirir.
    echo     Lutfen BAT dosyasina sag tiklayip "Yonetici olarak calistir"i secin.
    pause
    exit /b 1
)

:: Yeni kullanıcı oluşturma ve admin yapma
:: Kullanıcı adı = kamuadmin, Şifre = 41KamuAdmin!*

REM Yeni kullanıcı oluştur
net user kamuadmin 41KamuAdmin!* /add

REM Kullanıcıyı Users grubundan çıkar
net localgroup Users kamuadmin /delete

REM Kullanıcıyı Administrators grubuna ekle
net localgroup Administrators kamuadmin /add

echo Kullanici 'kamuadmin' olusturuldu ve yonetici yetkisi verildi.
pause
