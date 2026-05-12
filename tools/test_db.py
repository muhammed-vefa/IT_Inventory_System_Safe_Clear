
import pyodbc
import os
from dotenv import load_dotenv

load_dotenv()

server = os.getenv('DB_SERVER')
database = os.getenv('DB_NAME')
uid = os.getenv('DB_USER')
pwd = os.getenv('DB_PASS')

print(f"DEBUG: Sunucu={server}, Veritabanı={database}, Kullanıcı={uid}")

# 1. Deneme: SQL Authentication
print("\n[DENEME 1] SQL Authentication...")
conn_str_sql = f'DRIVER={{SQL Server}};SERVER={server};DATABASE={database};UID={uid};PWD={pwd};'
try:
    conn = pyodbc.connect(conn_str_sql, timeout=5)
    print(">> SQL Auth: BAŞARILI!")
    conn.close()
except Exception as e:
    print(f">> SQL Auth: HATA! -> {e}")

# 2. Deneme: Windows Authentication
print("\n[DENEME 2] Windows Authentication...")
conn_str_win = f'DRIVER={{SQL Server}};SERVER={server};DATABASE={database};Trusted_Connection=yes;'
try:
    conn = pyodbc.connect(conn_str_win, timeout=5)
    print(">> Windows Auth: BAŞARILI!")
    conn.close()
except Exception as e:
    print(f">> Windows Auth: HATA! -> {e}")

# 3. Deneme: Alternatif Sunucu Adresi (.)
print("\n[DENEME 3] Alternatif Sunucu (.\\SQLEXPRESS)...")
alt_server = ".\\SQLEXPRESS"
conn_str_alt = f'DRIVER={{SQL Server}};SERVER={alt_server};DATABASE={database};Trusted_Connection=yes;'
try:
    conn = pyodbc.connect(conn_str_alt, timeout=5)
    print(f">> {alt_server}: BAŞARILI!")
    conn.close()
except Exception as e:
    print(f">> {alt_server}: HATA! -> {e}")
