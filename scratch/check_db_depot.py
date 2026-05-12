import sqlite3
import os

db_path = r'C:\Users\MUHAMMED-VEFA-IS\.gemini\antigravity\scratch\IT_Inventory_System\database\inventory.db'
if not os.path.exists(db_path):
    print("Database not found!")
    exit()

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("--- DEPOT ITEMS ---")
items = cursor.execute("SELECT * FROM depot_items").fetchall()
for i in items:
    print(f"ID: {i['id']}, Name: {i['name']}, Category: {i['category']}, Stock: {i['current_stock']}")

print("\n--- TRANSACTIONS ---")
trans = cursor.execute("SELECT COUNT(*) FROM depot_transactions").fetchone()
print(f"Total Transactions: {trans[0]}")

conn.close()
