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
    print("--- DEPOT ITEMS ---")
    items = query_db("SELECT * FROM depot_items")
    if not items:
        print("Depot table is EMPTY!")
    else:
        for i in items:
            print(f"ID: {i['id']}, Name: {i['name']}, Category: {i['category']}, Stock: {i['current_stock']}")

    print("\n--- INVENTORY STATS ---")
    inv = query_db("SELECT COUNT(*) as count FROM inventory", one=True)
    print(f"Total Inventory Items: {inv['count']}")

except Exception as e:
    print(f"Error: {e}")
