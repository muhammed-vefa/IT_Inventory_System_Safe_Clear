import os
from dotenv import load_dotenv
load_dotenv()
from core.database_sql import query_db

try:
    res = query_db("SELECT COUNT(*) FROM audit_logs")
    print(f"Total logs: {res[0][0]}")
    res = query_db("SELECT TOP 5 * FROM audit_logs ORDER BY created_at DESC")
    for r in res:
        print(dict(r))
except Exception as e:
    print(f"Error: {e}")
