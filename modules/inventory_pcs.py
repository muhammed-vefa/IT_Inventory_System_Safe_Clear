from flask import Blueprint, jsonify, request
from core.database_sql import query_db, get_db_connection
from core.auth import require_auth, require_admin, require_editor
from core.permissions import require_operation
from datetime import datetime
from modules.inventory_core import get_table_for_type, map_db_to_frontend, get_safe_columns, check_column_exists
import json
import os

_KEYOS_MAP_CACHE = None
_KEYOS_FILE_MTIME = 0

def get_cached_keyos_map():
    global _KEYOS_MAP_CACHE, _KEYOS_FILE_MTIME
    keyos_path = os.path.join(os.path.abspath(os.path.dirname(os.path.dirname(__file__))), "database", "data", "keyos_weekly_status.json")
    if not os.path.exists(keyos_path): return {}
    
    current_mtime = os.path.getmtime(keyos_path)
    if _KEYOS_MAP_CACHE is not None and current_mtime == _KEYOS_FILE_MTIME:
        return _KEYOS_MAP_CACHE
        
    try:
        with open(keyos_path, 'r', encoding='utf-8') as f:
            keyos_data = json.load(f)
        keyos_map = {}
        for dev in keyos_data.get("devices", []):
            sn = str(dev.get("Seri_No", "")).strip().upper()
            ip = str(dev.get("IP_Adresi", "")).strip()
            host = str(dev.get("Hostname", "")).strip().upper()
            last_act = dev.get("Son_Guncelleme", "-")
            if sn and sn != "-": keyos_map[sn] = last_act
            if ip and ip != "-": keyos_map[ip] = last_act
            if host and host != "-": keyos_map[host] = last_act
        _KEYOS_MAP_CACHE = keyos_map
        _KEYOS_FILE_MTIME = current_mtime
        return keyos_map
    except Exception as e:
        print(f"[KeyOS Cache Error] {e}")
        return {}

inventory_pcs_bp = Blueprint('inventory_pcs', __name__)

@inventory_pcs_bp.route('/pcs', methods=['GET'])
@require_auth
def get_pcs():
    try:
        from core.utils import success_response, error_response
        table = "pcs"
        requested = [
            "id", "pc_no", "location_code", "on_field", "warehouse", "is_faulty", 
            "without_location", "pending_installation", "ip", "mac", "pc_serial", 
            "monitor_serial", "monitor2_serial", "windows", "keyos", "rdp", 
            "pr6900", "pr5200", "pr8690", "by_serial", "bo_serial", "scanner_serial", 
            "description", "last_counted_at", "counted_by", "hostname", "device_type", 
            "last_edit_date", "last_edit_user", "hostname_mismatch", "created_at",
            "connected_printers", "keyos", "rdp_address", "rdp_reason", "is_deleted"
        ]
        cols = get_safe_columns(table, requested)
        include_archived = request.args.get('include_archived') == 'true'
        
        if include_archived:
            where_clause = "WHERE 1=1" if check_column_exists(table, "is_deleted") else ""
        else:
            where_clause = f"WHERE (p.is_deleted = 0 OR p.is_deleted IS NULL)" if check_column_exists(table, "is_deleted") else ""
        
        query = f"""
            SELECT p.{cols.replace(', ', ', p.')}, 
                   m.location_name, m.tower as tower, m.floor as floor, m.phone_number
            FROM {table} p
            LEFT JOIN mahal_list m ON p.location_code = m.location_code
            {where_clause}
            ORDER BY p.pc_no ASC
        """
        items = query_db(query)
        if items:
            items = [map_db_to_frontend(item, "pcs") for item in items]
            
            # --- KeyOS Last Active Merge ---
            try:
                keyos_map = get_cached_keyos_map()
                for item in items:
                    sn = str(item.get("pc_serial", "")).strip().upper()
                    ip = str(item.get("ip", "")).strip()
                    host = str(item.get("hostname", "")).strip().upper()
                    
                    k_val = keyos_map.get(sn) or keyos_map.get(ip) or keyos_map.get(host)
                    if k_val:
                        item["keyos_last_active"] = k_val
            except Exception as e:
                print(f"[KeyOS Merge Error] {e}")

        return success_response(items if items is not None else [])
    except Exception as e:
        print(f"[API ERROR] get_pcs: {e}")
        return error_response(f"Sistem Hatası: {str(e)}", code=500)


# =====================================================
#  SIRAMATIKLER (queing_machines)
# =====================================================

