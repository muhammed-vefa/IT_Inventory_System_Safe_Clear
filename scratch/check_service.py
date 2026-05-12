import sys
import os

# Set environment variables for the test
os.environ['DB_SERVER'] = r'LOCALHOST\SQLEXPRESS'
os.environ['DB_NAME'] = 'IT_INVENTORY'
os.environ['DB_USER'] = 'vefa'
os.environ['DB_PASS'] = '-*-94Vefa'

# Uygulama kök dizinini path'e ekle
sys.path.append(r'C:\Users\MUHAMMED-VEFA-IS\.gemini\antigravity\scratch\IT_Inventory_System')

from core.database_sql import query_db

try:
    print("--- PRINTER SERVICE RECORDS ---")
    items = query_db("SELECT * FROM printer_service")
    if not items:
        print("Printer Service table is EMPTY!")
    else:
        print(f"Found {len(items)} records.")
        for i in items[:10]: # İlk 10 tanesini göster
            print(f"ID: {i['id']}, PR_NO: {i['pr_no']}, Status: {i['status']}, Fault: {i['fault_desc']}")

    print("\n--- PRINTERS STATS ---")
    pr = query_db("SELECT COUNT(*) as count FROM printers", one=True)
    print(f"Total Printers: {pr['count']}")

except Exception as e:
    print(f"Error: {e}")
