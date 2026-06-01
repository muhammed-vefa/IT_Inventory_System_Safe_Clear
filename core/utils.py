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
        
    # --- Date Formatting ---
    date_fields = ["created_at", "sent_date", "return_date", "acquisition_date", "archive_date", "deleted_at", "last_counted_at"]
    datetime_fields = ["last_login", "last_activity", "last_edit_date"]
    
    for field in date_fields:
        val = row.get(field)
        if isinstance(val, datetime.datetime):
            row[field] = val.strftime("%d.%m.%Y")
            
    for field in datetime_fields:
        val = row.get(field)
        if isinstance(val, datetime.datetime):
            row[field] = val.strftime("%d.%m.%Y %H:%M")
        elif isinstance(val, str):
            try:
                # Try to parse English formats like 'May 22 2026 10:35AM'
                dt = datetime.datetime.strptime(val, "%b %d %Y %I:%M%p")
                row[field] = dt.strftime("%d.%m.%Y %H:%M")
            except:
                try:
                    dt = datetime.datetime.strptime(val, "%Y-%m-%d %H:%M:%S")
                    row[field] = dt.strftime("%d.%m.%Y %H:%M")
                except Exception as inner_e:
                    print(f"[Date Parse Warning] Could not parse date {val}: {inner_e}")

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
