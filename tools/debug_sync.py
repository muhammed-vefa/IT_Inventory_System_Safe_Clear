import os
import sys
import traceback
import sqlite3

# ANA DIZIN TESPITI (Nerede olursa olsun bir üst dizini veya ana dizini bulur)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Eğer tools klasörü içindeyse bir üst klasöre çık
if os.path.basename(BASE_DIR) == 'tools':
    BASE_DIR = os.path.dirname(BASE_DIR)

sys.path.append(BASE_DIR)

print("="*50)
print("   IT ENVANTER - GÜÇLENDİRİLMİŞ HATA TESPİTİ")
print("="*50)
print(f"Çalışma Dizini: {BASE_DIR}")

try:
    from core.sync_manager import SyncManager
    from core.database_sql import init_db, DB_PATH
    
    # Veritabanı yolunu tam yol (absolute) olarak belirle
    ABS_DB_PATH = os.path.join(BASE_DIR, 'database', 'inventory.db')
    print(f"Veritabanı Yolu: {ABS_DB_PATH}")

    if not os.path.exists(os.path.dirname(ABS_DB_PATH)):
        print("[UYARI] Database klasörü yok, oluşturulmaya çalışılıyor...")
        os.makedirs(os.path.dirname(ABS_DB_PATH), exist_ok=True)

    print("[1/2] Veritabanı bağlantısı test ediliyor...")
    conn = sqlite3.connect(ABS_DB_PATH)
    conn.close()
    print("[BAŞARI] Veritabanına erişildi.")

    print("[2/2] Senkronizasyon başlatılıyor...")
    print("-" * 30)
    
    sync_mgr = SyncManager(BASE_DIR)
    stats = sync_mgr.sync_inventory()
    
    print("-" * 30)
    print(f"İŞLEM TAMAMLANDI: {stats}")

except Exception as e:
    print("\n" + "!"*20 + " HATA " + "!"*20)
    print(f"Mesaj: {str(e)}")
    traceback.print_exc()

print("\nKapatmak için Enter'a basın...")
input()
