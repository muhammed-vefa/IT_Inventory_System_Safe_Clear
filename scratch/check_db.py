import sqlite3
import os

db_path = r'C:\Users\MUHAMMED-VEFA-IS\.gemini\antigravity\scratch\IT_Inventory_System\database\inventory.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    rows = cursor.execute("SELECT id, pc_no, mahal_adi FROM inventory LIMIT 5").fetchall()
    for row in rows:
        print(f"ID: {row['id']}, PC_NO: {row['pc_no']}, Mahal: {row['mahal_adi']}")
    conn.close()
else:
    print("DB not found")
