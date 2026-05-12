from flask import Blueprint, jsonify, request
from core.database_sql import get_db_connection

areas_manager_bp = Blueprint('areas_manager', __name__)

@areas_manager_bp.route('/get_all', methods=['GET'])
def get_all():
    conn = get_db_connection()
    if not conn: return jsonify([])
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM shared_areas")
    columns = [column[0] for column in cursor.description]
    results = [dict(zip(columns, row)) for row in cursor.fetchall()]
    conn.close()
    return jsonify(results)
