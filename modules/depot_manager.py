from flask import Blueprint, jsonify, request
from core.database_sql import get_db_connection

depot_manager_bp = Blueprint('depot_manager', __name__)

@depot_manager_bp.route('/get_all', methods=['GET'])
def get_all():
    conn = get_db_connection()
    if not conn: return jsonify([])
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM depot_items")
    columns = [column[0] for column in cursor.description]
    results = [dict(zip(columns, row)) for row in cursor.fetchall()]
    conn.close()
    return jsonify(results)

def sync_depot_from_excel_internal():
    return 0
