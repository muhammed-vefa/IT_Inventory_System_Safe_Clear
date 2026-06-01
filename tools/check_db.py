import os
import sys
# Path patch for sub-folder execution
project_root = os.path.dirname(os.path.abspath(__file__))
if os.path.basename(project_root) == 'tools':
    project_root = os.path.dirname(project_root)
if project_root not in sys.path:
    sys.path.append(project_root)
os.chdir(project_root)

import pyodbc
import os
from dotenv import load_dotenv

BASE_DIR = project_root
env_path = os.path.join(BASE_DIR, ".env")
if not os.path.exists(env_path):
    env_path = os.path.join(BASE_DIR, "tools", ".env")
load_dotenv(env_path, override=True)

DB_SERVER = os.getenv("DB_SERVER", ".\\SQLEXPRESS").strip()
DB_NAME = os.getenv("DB_NAME", "IT_INVENTORY").strip()

def check():
    try:
        conn_str = f"DRIVER={{SQL Server}};SERVER={DB_SERVER};DATABASE={DB_NAME};Trusted_Connection=yes;"
        conn = pyodbc.connect(conn_str, timeout=5)
        cursor = conn.cursor()
        
        tables = ["pcs", "queing_machines", "tablets", "printers", "barcode_printers", "barcode_readers", "scanners"]
        for t in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {t} WHERE is_deleted = 0")
            count = cursor.fetchone()[0]
            print(f"Table {t}: {count} records")
            
            if t == "pcs" and count > 0:
                cursor.execute(f"SELECT TOP 1 pc_no, device_type FROM {t}")
                row = cursor.fetchone()
                print(f"  Sample PCS: pc_no={row[0]}, device_type={row[1]}")
        
        conn.close()
    except Exception as e:
        print(f"Hata: {e}")

if __name__ == "__main__":
    check()
