import sqlite3
import os

DB_PATH = "database/inventory.db"

def create_dummy_data():
    if not os.path.exists("database"):
        os.makedirs("database")
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Tabloları temizle
    tables = ["inventory", "printers", "knowledge_base", "users", "logs", "printer_service", "magicinfo_devices"]
    for t in tables:
        try: cursor.execute(f"DELETE FROM {t}")
        except: pass
    
    # Dummy Users
    cursor.execute("INSERT INTO users (username, password, role, display_name) VALUES (?,?,?,?)", 
                   ("admin", "admin123", "ADMIN", "Demo Admin"))
    cursor.execute("INSERT INTO users (username, password, role, display_name) VALUES (?,?,?,?)", 
                   ("editor", "editor123", "EDITOR", "Demo Editor"))
    
    # Dummy Inventory
    for i in range(1, 11):
        cursor.execute("""INSERT INTO inventory (pc_no, category, mahal_adi, ip, seri, status) 
                          VALUES (?,?,?,?,?,?)""", 
                       (f"PC-{i:03d}", "PC", f"Demo Mahal {i}", f"10.0.0.{10+i}", f"SN{1000+i}", "Kurulu"))
    
    # Dummy Printers
    for i in range(1, 6):
        cursor.execute("""INSERT INTO printers (pr_no, model, ip, status, mahal) 
                          VALUES (?,?,?,?,?)""", 
                       (f"PR-{i:03d}", "Demo Printer Model X", f"10.0.0.{50+i}", "Kurulu", f"Demo Mahal {i}"))
    
    # Dummy Knowledge Base
    cursor.execute("INSERT INTO knowledge_base (title, content, category) VALUES (?,?,?)", 
                   ("Yazıcı Kurulumu", "Demo içerik: Yazıcıyı kurmak için IP adresini girin.", "Yazıcı"))
    
    conn.commit()
    conn.close()
    print("Demo veriler başarıyla oluşturuldu.")

if __name__ == "__main__":
    create_dummy_data()
