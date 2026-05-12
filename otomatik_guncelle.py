import os
import time
import subprocess
import locale
from datetime import datetime

def get_encoding():
    """Sistemin varsayılan encoding'ini bulur."""
    return locale.getpreferredencoding() or 'utf-8'

def guncelle_ve_senkronize_et():
    encoding = get_encoding()
    print(f"[{datetime.now()}] GitHub kontrol ediliyor... (Sistem: {encoding})")
    
    # 1. Yerel değişiklikleri yedekle (Push)
    try:
        # Sadece değişen Excel ve Python dosyalarını önemse
        subprocess.run(["git", "add", "database/*.xlsx", "modules/*.py", "*.py", "*.html", "*.css"], stderr=subprocess.DEVNULL)
        
        status_local = subprocess.check_output(["git", "status", "--porcelain"]).decode(encoding, errors='ignore')
        if status_local:
            print("Yerel değişiklikler bulundu. GitHub'a yedekleniyor...")
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            subprocess.run(["git", "commit", "-m", f"Otomatik Yedekleme: {timestamp}"], stderr=subprocess.DEVNULL)
            subprocess.run(["git", "push", "origin", "main"], stderr=subprocess.DEVNULL)
            print("Yedekleme tamamlandı.")
    except Exception as e:
        print(f"Yedekleme Atlandı/Hata: {e}")

    # 2. GitHub'dan yeni kodları çek (Pull)
    try:
        # Önce uzak depoyu sorgula
        subprocess.run(["git", "fetch", "origin"], stderr=subprocess.DEVNULL)
        
        # Branch durumunu kontrol et
        status_remote = subprocess.check_output(["git", "status", "-uno"]).decode(encoding, errors='ignore')
        
        if "Your branch is behind" in status_remote or "can be fast-forwarded" in status_remote:
            print("Yeni kod bulundu! Sistem güncelleniyor...")
            
            # Çatışmayı önlemek için yerel değişiklikleri geçici olarak kenara al
            subprocess.run(["git", "stash"], stderr=subprocess.DEVNULL)
            
            # Sunucuyu kapat (Sadece pull yapmadan hemen önce)
            os.system('taskkill /F /FI "WINDOWTITLE eq IT Inventory System - Sunucu*" /T')
            time.sleep(2)
            
            # Kodları çek (Kritik: merge çatışması olursa üzerine yaz)
            subprocess.run(["git", "pull", "origin", "main", "-X", "theirs"], stderr=subprocess.DEVNULL)
            
            # Kenara aldığımız Excel değişikliklerini geri getir (Eğer varsa)
            subprocess.run(["git", "stash", "pop"], stderr=subprocess.DEVNULL)
            
            # Yeniden başlat
            print("Sistem yeni sürümle başlatılıyor...")
            os.system("start arkaplanda_baslat.vbs") # VBS üzerinden sessiz başlatma daha sağlıklı olabilir
            print("Güncelleme tamamlandı.")
        else:
            print("Kod güncel.")
    except Exception as e:
        print(f"Güncelleme Hatası: {e}")

# Döngü
if __name__ == "__main__":
    print("Otomatik Senkronizasyon Servisi Başlatıldı.")
    while True:
        try:
            guncelle_ve_senkronize_et()
        except Exception as e:
            print(f"Genel Hata: {e}")
        
        time.sleep(120) # 2 dakikada bir kontrol (Sunucu yükünü azaltmak için)
