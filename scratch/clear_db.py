from core.database_sql import get_db_connection

def clear_histories():
    try:
        conn = get_db_connection()
        print("Clearing audit_logs...")
        conn.execute("DELETE FROM audit_logs")
        print("Clearing depot_transactions...")
        conn.execute("DELETE FROM depot_transactions")
        conn.commit()
        conn.close()
        print("Done!")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    clear_histories()
