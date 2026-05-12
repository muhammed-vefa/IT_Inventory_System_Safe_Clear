from flask import Blueprint, jsonify, request
from core.database_sql import get_db_connection
mahal_manager_bp = Blueprint('mahal_manager', __name__)
@mahal_manager_bp.route('/get_all', methods=['GET'])
def get_all():
 # Mahal listesi (Datalist iin)
 conn = get_db_connection()
 cursor = conn.cursor()
 cursor.execute("SELECT DISTINCT mahal_kodu, mahal_adi FROM inventory")
 results = [row[0] for row in cursor.fetchall() if row[0]]
 conn.close()
 return jsonify(results)
