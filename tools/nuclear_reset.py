
import pyodbc
import os
from dotenv import load_dotenv

load_dotenv()

def nuclear_reset():
    print("="*60)
    print(" !!! TEHLIKELI BOLGE: VERI TABANI TAMAMEN SIFIRLANIYOR !!! ")
    print("="*60)
    
    confirm = input("TUM verileri (Envanter, Depo, Bilgi Bankasi, Ortak Alanlar vb.) silmek istediginize emin misiniz? (evet/hayir): ")
    if confirm.lower() != 'evet':
        print("Islem iptal edildi.")
        return

    server = os.getenv('DB_SERVER')
    database = os.getenv('DB_NAME')
    uid = os.getenv('DB_USER')
    pwd = os.getenv('DB_PASS')
    
    # 1. DENEME: SQL Authentication (vefa kullanicisi ile)
    conn_str = f'DRIVER={{SQL Server}};SERVER={server};DATABASE={database};UID={uid};PWD={pwd};'
    
    # 2. DENEME: Windows Authentication (Eger SQL login fail olursa)
    conn_str_trusted = f'DRIVER={{SQL Server}};SERVER={server};DATABASE={database};Trusted_Connection=yes;'
    
    tables_to_clean = [
        'inventory',
        'depot_transactions',
        'depot_items',
        'knowledge_base',
        'technical_notes',
        'shared_areas',
        'printer_service',
        'printer_service_history',
        'audit_logs',
        'printers',
        'note_images'
    ]

    try:
        # Once normal SQL Auth dene
        try:
            conn = pyodbc.connect(conn_str, timeout=5)
        except:
            # Olmazsa Windows Auth (Trusted) dene
            print("SQL Girisi basarisiz, Windows Auth ile baglaniliyor...")
            conn = pyodbc.connect(conn_str_trusted, timeout=5)
            
        cursor = conn.cursor()
        
        print("\nSifirlama islemi baslatildi...")
        
        for table in tables_to_clean:
            try:
                print(f" -> {table} temizleniyor...", end=" ")
                cursor.execute(f"DELETE FROM {table}")
                print("TAMAM")
            except Exception as e:
                print(f"HATA! ({e})")
        
        conn.commit()
        print("\n" + "="*60)
        print(" TEBRIKLER! Veri tabani tamamen temizlendi. ")
        print(" Simdi Dashboard uzerinden 'Tumunu Senkronize Et' diyebilirsiniz. ")
        print("="*60)
        conn.close()
        
    except Exception as e:
        print(f"\nKRITIK HATA: Veri tabanina baglanilamadi! -> {e}")

if __name__ == "__main__":
    nuclear_reset()
