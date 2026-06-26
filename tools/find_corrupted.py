import sys
sys.path.append('.')
from core.database_sql import get_db_connection

conn = get_db_connection('IT_INVENTORY')
if not conn:
    print("Baglanti saglanamadi!")
    sys.exit(1)

c = conn.cursor()
c.execute("SELECT id, pr_no, model, mac, ip FROM printers WHERE ip LIKE '%Brother%' OR mac LIKE '%PR%'")
rows = c.fetchall()

print(f"Bulunan bozuk kayit sayisi: {len(rows)}")
for r in rows[:20]:
    print(r)
