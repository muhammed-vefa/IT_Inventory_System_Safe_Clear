import os
import sys
# Path patch for sub-folder execution
project_root = os.path.dirname(os.path.abspath(__file__))
if os.path.basename(project_root) == 'tools':
    project_root = os.path.dirname(project_root)
if project_root not in sys.path:
    sys.path.append(project_root)
os.chdir(project_root)

# -*- coding: utf-8 -*-
import os
import pyodbc
from dotenv import load_dotenv

BASE_DIR = project_root
env_path = os.path.join(BASE_DIR, ".env")
if not os.path.exists(env_path):
    env_path = os.path.join(BASE_DIR, "tools", ".env")
load_dotenv(env_path, override=True)

DB_SERVER = os.getenv("DB_SERVER", ".\\SQLEXPRESS").strip()
DB_NAME = os.getenv("DB_NAME", "IT_INVENTORY").strip()
DB_USER = os.getenv("DB_USER", "").strip()
DB_PASS = os.getenv("DB_PASS", "").strip()

def clear_all_data():
    tables_to_clear = [
        "pcs", "printers", "barcode_printers", "barcode_readers", "scanners",
        "monitors", "tablets", "queing_machines",
        "printer_service", "printer_service_history", "technical_notes",
        "closure_notes", "troubleshooting_notes", "shared_areas",
        "depot_items", "consumable_items", "mahal_list", "audit_logs",
        "refresh_tokens", "user_activity_log", "users", "sync_status", "sync_logs"
    ]
    
    print(f"\n[*] {DB_NAME} Veritabani Temizleniyor...")
    
    try:
        if DB_USER and DB_PASS:
            conn_str = f"DRIVER={{SQL Server}};SERVER={DB_SERVER};DATABASE={DB_NAME};UID={DB_USER};PWD={DB_PASS};"
        else:
            conn_str = f"DRIVER={{SQL Server}};SERVER={DB_SERVER};DATABASE={DB_NAME};Trusted_Connection=yes;"
            
        conn = pyodbc.connect(conn_str, timeout=10)
        cursor = conn.cursor()
        
        # Foreign Key kısıtlamalarını devre dışı bırak
        try:
            cursor.execute("EXEC sp_MSforeachtable 'ALTER TABLE ? NOCHECK CONSTRAINT ALL'")
        except: pass
        
        for table in tables_to_clear:
            try:
                # Tabloyu tamamen sil (DROP TABLE) ki bozuk/fazla sütunlar da yok olsun
                cursor.execute(f"IF EXISTS (SELECT * FROM sysobjects WHERE name='{table}' AND xtype='U') DROP TABLE [{table}]")
                print(f"  [OK] {table} tablosu tumden silindi (DROP).")
            except Exception as e:
                print(f"  [HATA] {table} silinemedi: {e}")
        
        # Kısıtlamaları tekrar aç
        try:
            cursor.execute("EXEC sp_MSforeachtable 'ALTER TABLE ? CHECK CONSTRAINT ALL'")
        except: pass
        
        conn.commit()
        conn.close()
        print("\n[✓] TUM VERILER (KULLANICILAR DAHIL) BASARIYLA TEMIZLENDI.")
        
    except Exception as e:
        print(f"\n[!] Kritik Hata: {e}")

if __name__ == "__main__":
    # Parametreli calistirma kontrolü (promptu atlamak için)
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--force":
        clear_all_data()
    else:
        confirm = input("TUM ENVANTER VERILERI SILINECEK! Emin misiniz? (E/H): ")
        if confirm.lower() == 'e':
            clear_all_data()
        else:
            print("[!] Islem iptal edildi.")
