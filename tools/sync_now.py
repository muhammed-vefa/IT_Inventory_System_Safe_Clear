import sys
import os

# Proje ana dizinini sys.path'e ekle
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from main import sync_excel_to_db
    from core.database_sql import init_db
    
    print("--- IT ENVANTER SENKRONIZASYON SERVISI (DESKTOP) ---")
    print("[1/2] Veritabani semasi kontrol ediliyor...")
    init_db()
    
    print("[2/2] Excel verileri aktariliyor...")
    stats = sync_excel_to_db()
    
    print("\n" + "="*40)
    print("      SENKRONIZASYON TAMAMLANDI")
    print("="*40)
    print(f"PC Envanter   : {stats.get('pc_read', 0)} okundu, {stats.get('pc_synced', 0)} aktarildi.")
    print(f"Ek Cihazlar   : {stats.get('ek_synced', 0)} cihaz (Tablet/Sira.) guncellendi.")
    print(f"Yazici/Donanim: {stats.get('printer_synced', 0)} cihaz guncellendi.")
    print(f"Servis Kaydi  : {stats.get('service_synced', 0)} kayit islendi.")
    print(f"Depo Stok     : {stats.get('depot_synced', 0)} kalem guncellendi.")
    
    if stats.get('warnings'):
        print("\nUYARILAR:")
        for w in stats['warnings']:
            print(f" ! {w}")
            
    print("="*40)

except Exception as e:
    print(f"\n[HATA] Islem basarisiz oldu: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
