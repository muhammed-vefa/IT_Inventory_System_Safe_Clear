from flask import Blueprint, jsonify, request
from core.database_sql import query_db, get_db_connection
from core.auth import require_auth, require_admin, require_editor
from core.permissions import require_operation
from datetime import datetime
from modules.inventory_core import get_table_for_type, map_db_to_frontend, get_safe_columns, check_column_exists

inventory_mahal_bp = Blueprint('inventory_mahal', __name__)

@inventory_mahal_bp.route('/mahal_list', methods=['GET'])
@require_auth
def get_mahal_list():
    try:
        results = query_db("SELECT * FROM mahal_list ORDER BY location_code ASC")
        if results:
            for r in results:
                if 'location_code' in r and 'location_code' not in r:
                    r['location_code'] = r['location_code']
        return jsonify(results if results is not None else [])
    except Exception as e:
        print(f"[API ERROR] mahal_list: {e}")
        return jsonify([]), 500



