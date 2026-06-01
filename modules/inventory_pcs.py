from flask import Blueprint, jsonify, request
from core.database_sql import query_db, get_db_connection
from core.auth import require_auth, require_admin, require_editor
from core.permissions import require_operation
from datetime import datetime
from modules.inventory_core import get_table_for_type, map_db_to_frontend, get_safe_columns, check_column_exists

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
            "connected_printers", "keyos", "rdp_address", "rdp_reason"
        ]
        cols = get_safe_columns(table, requested)
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
        return success_response(items if items is not None else [])
    except Exception as e:
        print(f"[API ERROR] get_pcs: {e}")
        return error_response(f"Sistem Hatası: {str(e)}", code=500)


# =====================================================
#  SIRAMATIKLER (queing_machines)
# =====================================================

