import sys
import os
sys.path.append(os.path.abspath('.'))

from core.database_sql import get_db_connection

conn = get_db_connection()
cursor = conn.cursor()
cursor.execute("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'printers'")
cols = [row[0] for row in cursor.fetchall()]
print("PRINTERS COLUMNS:")
print(cols)

cursor.execute("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'pcs'")
cols_pcs = [row[0] for row in cursor.fetchall()]
print("\nPCS COLUMNS:")
print(cols_pcs)
conn.close()
