from flask import Blueprint, jsonify, request
from core.database_sql import query_db, get_db_connection
from core.auth import require_auth, require_admin, require_editor
from core.permissions import require_operation
from datetime import datetime
from modules.inventory_core import get_table_for_type, map_db_to_frontend, get_safe_columns, check_column_exists

inventory_queing_bp = Blueprint('inventory_queing', __name__)

@inventory_queing_bp.route('/queing_machines', methods=['GET'])
@require_auth
def get_queing_machines():
    try:
        from core.utils import success_response
        table = "queing_machines"
        loc_col = "location_code" if check_column_exists(table, "location_code") else "location_code"
        requested = [
            "id", "pc_no", loc_col, "on_field", "warehouse", "is_faulty", 
            "without_location", "pending_installation", "ip", "mac", "serial_no"
        ]
        cols = get_safe_columns(table, requested)
        where_clause = f"WHERE (q.is_deleted = 0 OR q.is_deleted IS NULL)" if check_column_exists(table, "is_deleted") else ""
        
        query = f"""
            SELECT q.{cols.replace(', ', ', q.')}, q.{loc_col} as location_code, 
                   m.location_name, m.tower as tower, m.floor as floor, m.phone_number
            FROM {table} q
            LEFT JOIN mahal_list m ON q.{loc_col} = m.location_code
            {where_clause}
            ORDER BY q.pc_no ASC
        """
        items = query_db(query)
        if items:
            items = [map_db_to_frontend(item, "queing_machines") for item in items]
            for i in items: i['device_type'] = 'SIRAMATIK'
        return success_response(items if items is not None else [])
    except Exception as e:
        print(f"[API ERROR] get_queing_machines: {e}")
        return jsonify([]), 500


# =====================================================
#  TABLETLER (tablets)
# =====================================================

