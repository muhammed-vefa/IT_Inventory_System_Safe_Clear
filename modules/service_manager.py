from flask import Blueprint, jsonify, request
from core.database_sql import get_db_connection

service_manager_bp = Blueprint('service_manager', __name__)

@service_manager_bp.route('/get_all', methods=['GET'])
def get_all():
    conn = get_db_connection()
    if not conn: return jsonify([])
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM service_records ORDER BY id DESC")
    columns = [column[0] for column in cursor.description]
    results = [dict(zip(columns, row)) for row in cursor.fetchall()]
    conn.close()
    return jsonify(results)
