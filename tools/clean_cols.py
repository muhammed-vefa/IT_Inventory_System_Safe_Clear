import os
from dotenv import load_dotenv
from core.database_sql import get_db_connection

load_dotenv()

def clean_bogus_columns():
    conn = get_db_connection()
    if not conn: return
    cursor = conn.cursor()
    
    bogus_cols = ['mahalsiz', 'sahada', 'kurulu', 'depo', 'arizali', 'arızalı', 'kayip', 'kayıp', 'deleted', 'id_deletet', 'id_deleted', 'saha_stock', 'arizali_stock', 'kayip_stock']
    
    cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE='BASE TABLE'")
    tables = [r[0] for r in cursor.fetchall()]
    
    for t in tables:
        for c in bogus_cols:
            try:
                # Kolon var mi kontrol et
                cursor.execute(f"SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME='{t}' AND COLUMN_NAME='{c}'")
                if cursor.fetchone():
                    print(f"[*] Fazlalik kolon siliniyor: {t}.{c}")
                    cursor.execute(f"ALTER TABLE [{t}] DROP COLUMN [{c}]")
                    conn.commit()
            except Exception as e:
                print(f"Hata ({t}.{c}): {e}")

if __name__ == '__main__':
    clean_bogus_columns()
