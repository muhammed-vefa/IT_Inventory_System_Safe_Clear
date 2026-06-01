import os
import sys
import pyodbc
import re
from dotenv import load_dotenv

# Path patch for sub-folder execution
project_root = os.path.dirname(os.path.abspath(__file__))
if os.path.basename(project_root) == 'tools':
    project_root = os.path.dirname(project_root)
if project_root not in sys.path:
    sys.path.append(project_root)
os.chdir(project_root)

# Load env variables
env_path = os.path.join(project_root, ".env")
if not os.path.exists(env_path):
    env_path = os.path.join(project_root, "tools", ".env")
load_dotenv(env_path, override=True)

DB_SERVER = os.getenv("DB_SERVER", ".\\SQLEXPRESS").strip()
DB_NAME = os.getenv("DB_NAME", "IT_INVENTORY").strip()
DB_USER = os.getenv("DB_USER", "").strip()
DB_PASS = os.getenv("DB_PASS", "").strip()

def get_connection():
    if DB_USER and DB_PASS:
        conn_str = f"DRIVER={{SQL Server}};SERVER={DB_SERVER};DATABASE={DB_NAME};UID={DB_USER};PWD={DB_PASS};"
    else:
        conn_str = f"DRIVER={{SQL Server}};SERVER={DB_SERVER};DATABASE={DB_NAME};Trusted_Connection=yes;"
    return pyodbc.connect(conn_str, timeout=10)

def parse_pc_no_to_int(pc_no):
    if not pc_no:
        return 999999
    digits = re.findall(r'\d+', str(pc_no))
    if digits:
        return int(digits[0])
    return 999999

def update_database():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get all active PCs
    print("[*] Veritabanından bilgisayarlar çekiliyor...")
    cursor.execute("SELECT id, pc_no, location_code, hostname FROM pcs WHERE is_deleted = 0")
    pcs = cursor.fetchall()
    
    print(f"[*] Toplam {len(pcs)} adet aktif bilgisayar bulundu. Hostname güncellemeleri başlıyor...")
    
    # Group PCs by location_code for hostname sequence generation
    pcs_by_loc = {}
    for item in pcs:
        rid, pc_no, loc_code, host = item
        loc_code = str(loc_code).strip() if loc_code else ""
        if loc_code:
            if loc_code not in pcs_by_loc:
                pcs_by_loc[loc_code] = []
            pcs_by_loc[loc_code].append(item)
            
    host_update_count = 0
    
    for loc_code, pc_list in pcs_by_loc.items():
        # Sort PCs in this location by their pc_no value
        pc_list.sort(key=lambda x: parse_pc_no_to_int(x[1]))
        
        clean_loc = str(loc_code).replace('.', '').strip().upper()
        
        for idx, (rid, pc_no, _, current_host) in enumerate(pc_list, start=1):
            # Generate systematically: AB1T5230x01
            generated_host = f"{clean_loc}x{idx:02d}"
            if not current_host or str(current_host).strip().upper() in ('', 'NONE', 'NULL', '-') or str(current_host).strip() != generated_host:
                query = "UPDATE pcs SET hostname = ? WHERE id = ?"
                cursor.execute(query, (generated_host, rid))
                host_update_count += 1
                
    conn.commit()
    conn.close()
    
    print(f"\n==================================================")
    print(f"  GÜNCELLEME TAMAMLANDI!")
    print(f"  - Hostname adresi üretilen/güncellenen: {host_update_count} cihaz")
    print(f"==================================================")

if __name__ == '__main__':
    update_database()
