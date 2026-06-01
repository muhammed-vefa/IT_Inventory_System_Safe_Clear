import os
import sys

# Path patch for sub-folder execution
project_root = os.path.dirname(os.path.abspath(__file__))
if os.path.basename(project_root) == 'tools':
    project_root = os.path.dirname(project_root)
if project_root not in sys.path:
    sys.path.append(project_root)
os.chdir(project_root)

import pandas as pd
from dotenv import load_dotenv
from core.database_sql import get_db_connection

load_dotenv()

def export_all_to_excel():
    print("[*] Veritabanina baglaniliyor...")
    conn = get_db_connection()
    if not conn:
        print("[!] Baglanti hatasi!")
        return
        
    print("[*] Baglanti basarili. Tablolar cekiliyor...")
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sys.tables")
    tables = [row[0] for row in cursor.fetchall()]
    
    excel_file = "IT_Inventory_Tam_Dokum.xlsx"
    print(f"[*] Toplam {len(tables)} tablo bulundu. Tek bir Excel dosyasina (her tablo ayri bir sayfa olarak) yazdiriliyor...")
    
    with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
        for table in tables:
            print(f"  -> Tablo aktariliyor: {table}")
            df = pd.read_sql(f"SELECT * FROM {table}", conn)
            # Excel sayfa isimleri maksimum 31 karakter olabilir
            df.to_excel(writer, sheet_name=table[:31], index=False)
            
    conn.close()
    print(f"[+] Islem TAMAM. Butun verileriniz tek bir dosya icinde '{excel_file}' olarak kaydedildi.")

if __name__ == '__main__':
    export_all_to_excel()
