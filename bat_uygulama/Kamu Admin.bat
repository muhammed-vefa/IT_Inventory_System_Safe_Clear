@echo off
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
