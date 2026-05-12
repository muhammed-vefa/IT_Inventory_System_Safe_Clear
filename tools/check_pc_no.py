
import pyodbc
import os
from dotenv import load_dotenv

load_dotenv()

def check_inventory_data():
    server = os.getenv('DB_SERVER')
    database = os.getenv('DB_NAME')
    uid = os.getenv('DB_USER')
    pwd = os.getenv('DB_PASS')
    
    conn_str = f'DRIVER={{SQL Server}};SERVER={server};DATABASE={database};UID={uid};PWD={pwd};'
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        print("--- Envanter Durum Kontrolü ---")
        
        # 1. '---' olan kayıtları say
        cursor.execute("SELECT COUNT(*) FROM inventory WHERE pc_no = '---' OR pc_no IS NULL OR pc_no = ''")
        missing_count = cursor.fetchone()[0]
        
        # 2. Toplam kayıt
        cursor.execute("SELECT COUNT(*) FROM inventory")
        total_count = cursor.fetchone()[0]
        
        print(f"Toplam Kayıt: {total_count}")
        print(f"PC No Eksik/Hatalı (---): {missing_count}")
        
        # 3. Örnek kayıtları göster
        print("\nÖrnek Kayıtlar (İlk 5):")
        cursor.execute("SELECT TOP 5 id, pc_no, hostname, mahal_adi FROM inventory")
        for row in cursor.fetchall():
            print(f"ID: {row[0]} | PC No: {row[1]} | Hostname: {row[2]} | Mahal: {row[3]}")
            
        conn.close()
    except Exception as e:
        print(f"Hata: {e}")

if __name__ == "__main__":
    check_inventory_data()
