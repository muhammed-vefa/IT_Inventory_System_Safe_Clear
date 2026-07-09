import os
import sys
import random
import string
from datetime import datetime

# Path patch for sub-folder execution
project_root = os.path.dirname(os.path.abspath(__file__))
if os.path.basename(project_root) == 'tools':
    project_root = os.path.dirname(project_root)
if project_root not in sys.path:
    sys.path.append(project_root)
os.chdir(project_root)

from core.database_sql import get_db_connection, init_db

def generate_random_ip():
    return f"192.168.99.{random.randint(10, 250)}"

def generate_random_mac():
    return ":".join([f"{random.randint(0, 255):02X}" for _ in range(6)])

def generate_mock_data():
    print("[*] Veritabanı başlatılıyor...")
    init_db()
    
    conn = get_db_connection()
    if not conn:
        print("[!] Veritabanı bağlantısı kurulamadı. Lütfen .env dosyanızı kontrol edin.")
        return
        
    cursor = conn.cursor()
    
    try:
        print("[*] Sahte PC'ler (Bilgisayarlar) oluşturuluyor...")
        for i in range(1, 51):
            pc_no = f"PC-{i:03d}"
            location_code = random.choice(["KAT-1-MUHASEBE", "KAT-2-IT", "KAT-3-YONETIM", "ZEMIN-RESEPSIYON", "DEPO"])
            ip = generate_random_ip()
            mac = generate_random_mac()
            desc = "Test amacıyla oluşturulmuş sahte kayıttır."
            
            cursor.execute("""
                INSERT INTO pcs (pc_no, location_code, ip, mac, description, hostname)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (pc_no, location_code, ip, mac, desc, f"TEST-{pc_no}"))
            
        print("[*] Sahte Yazıcılar oluşturuluyor...")
        for i in range(1, 21):
            pr_no = f"PR-{i:03d}"
            location_code = random.choice(["KAT-1-MUHASEBE", "KAT-2-IT", "KAT-3-YONETIM", "ZEMIN-RESEPSIYON"])
            ip = generate_random_ip()
            mac = generate_random_mac()
            model = random.choice(["HP LaserJet Pro", "Canon i-SENSYS", "Epson EcoTank", "Brother HL-L2350DW"])
            
            cursor.execute("""
                INSERT INTO printers (pr_no, model, location_code, ip, mac)
                VALUES (?, ?, ?, ?, ?)
            """, (pr_no, model, location_code, ip, mac))
            
        print("[*] Sahte Mahal (Lokasyon) Listesi oluşturuluyor...")
        locations = [
            ("KAT-1-MUHASEBE", "1. Kat Muhasebe Departmanı", "1101"),
            ("KAT-2-IT", "2. Kat Bilgi İşlem", "1201"),
            ("KAT-3-YONETIM", "3. Kat Yönetim Kurulu", "1301"),
            ("ZEMIN-RESEPSIYON", "Zemin Kat Resepsiyon", "1001"),
            ("DEPO", "Ana Depo", "1002")
        ]
        
        for loc in locations:
            cursor.execute("""
                INSERT INTO mahal_list (location_code, location_name, phone_number)
                VALUES (?, ?, ?)
            """, loc)
            
        conn.commit()
        print("[✓] Tüm sahte veriler başarıyla eklendi! Sistemi test edebilirsiniz.")
        
    except Exception as e:
        print(f"[!] Hata oluştu: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    generate_mock_data()
