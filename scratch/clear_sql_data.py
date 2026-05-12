import os
from dotenv import load_dotenv
load_dotenv()
from core.database_sql import query_db, get_db_connection

def clear_data():
    conn = get_db_connection()
    try:
        # Kritik tabloları temizle (Users hariç)
        tables_to_clear = [
            "audit_logs",
            "printer_service",
            "printer_service_history",
            "inventory",
            "printers",
            "depot_items",
            "depot_transactions",
            "knowledge_base",
            "shared_areas",
            "technical_notes",
            "note_images"
        ]
        
        for table in tables_to_clear:
            print(f"{table} tablosu temizleniyor...")
            try:
                conn.execute(f"DELETE FROM {table}")
            except Exception as e:
                print(f"Uyarı: {table} silinirken hata oluştu (Tablo olmayabilir): {e}")
        
        conn.commit()
        print("\n[BAŞARI] Tüm veriler başarıyla temizlendi. Excel'den tekrar senkronize edebilirsiniz.")
    except Exception as e:
        print(f"Hata: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    clear_data()
