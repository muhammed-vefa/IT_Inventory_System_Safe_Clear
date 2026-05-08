import os
import time
import subprocess

def guncelle_ve_baslat():
    print("GitHub kontrol ediliyor...")
    subprocess.run(["git", "fetch", "origin"])
    
    # Branş ismini kontrol et (master mı main mi?)
    status = subprocess.check_output(["git", "status", "-uno"]).decode("utf-8")
    
    if "Your branch is behind" in status:
        print("Yeni kod bulundu! Güncelleniyor...")
        
        # 1. Önce eski çalışan uygulamayı kapat (Portu boşalt)
        # Pencere başlığına göre bulup kapatıyoruz
        os.system('taskkill /F /FI "WINDOWTITLE eq IT Inventory System - Sunucu*" /T')
        
        # 2. Kodları çek
        subprocess.run(["git", "pull", "origin", "main"])
        
        # 3. Yeni kodlarla başlat
        print("Sistem yeni sürümle başlatılıyor...")
        os.system("start baslat.bat")
        print("Güncelleme tamamlandı.")
    else:
        print("Kod güncel.")

while True:
    try:
        guncelle_ve_baslat()
    except Exception as e:
        print(f"Hata: {e}")
    
    time.sleep(60) # 1 dakikada bir kontrol et
