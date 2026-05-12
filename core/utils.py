import re
def _clean(val):
 if val is None: return ""
 return str(val).strip()
def _get(row, keys):
 for k in keys:
 k_upper = k.upper()
 if k_upper in row: return row[k_upper]
 return ""
def _norm_key(k):
 if not k: return ""
 return re.sub(r'[^a-zA-Z0-9]', '', str(k)).upper()
def _norm_pc_id(val):
 if not val: return ""
 s = str(val).strip().upper()
 if s.startswith('PC-'): return s
 if s.isdigit(): return f"PC-{s.zfill(3)}"
 return s
