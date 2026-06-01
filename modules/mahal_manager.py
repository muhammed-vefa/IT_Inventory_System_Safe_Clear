from core.utils import normalize_row
from flask import Blueprint, jsonify, request
from core.database_sql import get_db_connection

mahal_manager_bp = Blueprint('mahal_manager', __name__)

@mahal_manager_bp.route('/get_all', methods=['GET'])
def get_all():
    conn = get_db_connection()
    if not conn: return jsonify([])
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM mahal_list ORDER BY location_code ASC")
    columns = [column[0] for column in cursor.description]
    results = [dict(zip(columns, row)) for row in cursor.fetchall()]
    conn.close()
    return jsonify(results)
