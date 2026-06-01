import sys
import os
sys.path.append(os.getcwd())

from core.database_sql import get_db_connection
from dotenv import load_dotenv

load_dotenv()

try:
    conn = get_db_connection()
    cur = conn.cursor()

    print("--- Depot Items (Barcode) ---")
    cur.execute("SELECT name, current_stock, category FROM depot_items WHERE name LIKE '%BARKOD%'")
    for r in cur.fetchall():
        print(dict(zip([column[0] for column in cur.description], r)))

    print("\n--- Printers (C230/G2090) ---")
    cur.execute("SELECT model, status, pr_no FROM printers WHERE model LIKE '%C230%' OR model LIKE '%G2090%' OR pr_no LIKE '%C230%' OR pr_no LIKE '%G2090%'")
    for r in cur.fetchall():
        print(dict(zip([column[0] for column in cur.description], r)))

    conn.close()
except Exception as e:
    print(f"Error: {e}")
