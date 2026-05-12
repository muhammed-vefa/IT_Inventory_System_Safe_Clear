import os
import sys

# Proje kok dizinini ekle
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from main import sync_excel_to_db_internal, sync_db_to_excel
    print("--- VERI SENKRONIZASYONU VE YEDEKLEME ---")
    
    print("1. Excel -> Veritabanı aktarılıyor...")
    stats = sync_excel_to_db_internal()
    print(f"Bitti: {stats}")
    
    print("\n2. Veritabanı -> Excel (Yedek) aktarılıyor...")
    sync_db_to_excel()
    print("Yedekleme tamamlandı (database/yedek_database klasörüne bakınız).")

except Exception as e:
    print(f"Hata: {e}")
    import traceback
    traceback.print_exc()

input("\nDevam etmek icin bir tusa basin...")
