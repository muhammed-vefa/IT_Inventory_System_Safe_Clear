import pandas as pd
import os
from core.utils import _clean
def read_excel_data(file_path, sheet_name=0):
 if not os.path.exists(file_path): return []
 try:
 df = pd.read_excel(file_path, sheet_name=sheet_name)
 df = df.where(pd.notnull(df), None)
 data = df.to_dict('records')
 return [_clean_dict(r) for r in data]
 except Exception as e:
 print(f"Excel okuma hatas ({file_path}): {e}")
 return []
def _clean_dict(d):
 return {str(k).strip().upper(): (str(v).strip() if v is not None else None) for k, v in d.items()}
