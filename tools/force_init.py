import sys
import os

base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_dir)

try:
    from core.database_sql import init_db
    print("Running init_db()...")
    init_db()
    print("init_db() completed successfully!")
except Exception as e:
    print(f"Error: {e}")
