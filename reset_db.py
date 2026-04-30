import sys
import os

# Mevcut dizini path'e ekle
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from core.database_sql import get_db_connection
    from main import sync_excel_to_db
    print("Veritabanı bağlantısı kuruluyor...")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Silinecek tablolar
    tables = [
        "inventory", 
        "printers", 
        "depot_items", 
        "printer_service", 
        "knowledge_base", 
        "shared_areas",
        "magicinfo_devices"
    ]
    
    print("\n--- MEVCUT VERİLER SİLİNİYOR ---")
    for table in tables:
        try:
            print(f"{table} tablosu temizleniyor...")
            cursor.execute(f"DELETE FROM {table}")
        except Exception as e:
            print(f"Hata ({table}): {e}")
    
    conn.commit()
    print("Tüm veriler başarıyla silindi.")
    
    print("\n--- EXCEL'DEN VERİLER AKTARILIYOR ---")
    sync_excel_to_db()
    
    print("\n[BAŞARILI] İşlem tamamlandı. Veritabanı Excel dosyaları ile güncellendi.")
    
except Exception as e:
    print(f"\n[HATA] Bir sorun oluştu: {e}")
    input("Devam etmek için bir tuşa basın...")
finally:
    if 'conn' in locals():
        conn.close()
