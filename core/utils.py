from flask import jsonify

import datetime

def success_response(data=None, message=None):
    resp = {
        "success": True,
        "data": data if data is not None else {},
        "message": message,
        "error": None,
        "timestamp": datetime.datetime.now().isoformat()
    }
    return jsonify(resp), 200

def error_response(message="Operation failed", details=None, code=400):
    resp = {
        "success": False,
        "data": {},
        "message": None,
        "error": message,
        "details": details,
        "timestamp": datetime.datetime.now().isoformat()
    }
    return jsonify(resp), code

def normalize_row(row):
    """
    Compatibility layer for transitioning from 'arizali' to 'is_faulty' in the database.
    Also formats all datetime fields to 'DD.MM.YYYY'.
    """
    if not isinstance(row, dict):
        return row

    # Ensure all keys are checked case-insensitively
    key_map = {k.lower(): k for k in row.keys()}

    # --- Clean "0" and "0.0" serial values ---
    serial_fields = [
        'pc_serial', 'by_serial', 'bo_serial', 'scanner_serial', 'monitor_serial', 'monitor2_serial',
        'serial_no', 'seri', 'by_seri', 'bo_seri', 'tarayici_seri', 'monitor_seri', 'monitor2_seri'
    ]
    for field in serial_fields:
        actual_key = key_map.get(field.lower())
        if actual_key and row[actual_key] is not None:
            s = str(row[actual_key]).strip()
            if s in ('0', '0.0', '0,0'):
                row[actual_key] = ''
        
    # --- Date Formatting ---
    date_fields = ["created_at", "sent_date", "return_date", "acquisition_date", "archive_date", "deleted_at", "last_counted_at"]
    datetime_fields = ["last_login", "last_activity", "last_edit_date", "timestamp"]
    
    for field in date_fields:
        actual_key = key_map.get(field.lower())
        if actual_key:
            val = row[actual_key]
            if isinstance(val, datetime.datetime):
                row[actual_key] = val.strftime("%d.%m.%Y")
            
    for field in datetime_fields:
        actual_key = key_map.get(field.lower())
        if actual_key:
            val = row[actual_key]
            if isinstance(val, datetime.datetime):
                row[actual_key] = val.strftime("%d.%m.%Y %H:%M")
            elif isinstance(val, str):
                parsed = False
                for fmt in [
                    "%b %d %Y %I:%M%p",
                    "%Y-%m-%d %H:%M:%S",
                    "%Y-%m-%d %H:%M:%S.%f",
                    "%Y-%m-%dT%H:%M:%S",
                    "%Y-%m-%dT%H:%M:%S.%f",
                    "%a, %d %b %Y %H:%M:%S %Z",
                    "%a, %d %b %Y %H:%M:%S GMT",
                    "%d.%m.%Y %H:%M"
                ]:
                    try:
                        dt = datetime.datetime.strptime(val, fmt)
                        row[actual_key] = dt.strftime("%d.%m.%Y %H:%M")
                        parsed = True
                        break
                    except ValueError:
                        continue
                if not parsed:
                    print(f"[Date Parse Warning] Could not parse datetime string: {val}")

    # --- Faulty Status Normalization ---
    val1 = row.get("is_faulty")
    val2 = row.get("arizali")
    val3 = row.get("arızalı")
    
    def is_true(v):
        if isinstance(v, bool): return v
        if isinstance(v, int): return v == 1
        if isinstance(v, str): return v.lower() in ('1', 'true', 'evet', 'var', 'arızalı', 'arizali')
        return False
        
    is_faulty = is_true(val1) or is_true(val2) or is_true(val3)
    
    if "is_faulty" in row or "arizali" in row or "arızalı" in row:
        row["is_faulty"] = is_faulty
        row["arizali"] = is_faulty
    
    return row
