import os
import sys
from dotenv import load_dotenv

# IT Inventory System yollarını ekle
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

load_dotenv()

from main import sync_excel_to_db
from core.database_sql import query_db

def test_sync():
    print("Starting Manual Sync Test...")
    try:
        sync_excel_to_db()
        print("Sync completed.")
        count = query_db("SELECT COUNT(*) as cnt FROM inventory", one=True)
        print(f"Inventory count in DB: {count['cnt']}")
        
        items = query_db("SELECT TOP 5 id, pc_no, mahal_adi FROM inventory")
        print("Sample items:")
        for item in items:
            print(f"  - ID: {item['id']}, PC: {item['pc_no']}, Mahal: {item['mahal_adi']}")
            
    except Exception as e:
        import traceback
        print(f"Sync Error: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    test_sync()
