from core.utils import normalize_row
from flask import Blueprint, jsonify, request
from core.database_sql import get_db_connection, query_db
from core.auth import require_admin

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

@mahal_manager_bp.route('/add', methods=['POST'])
@require_admin
def add_mahal():
    data = request.json
    location_code = data.get('location_code')
    mimari_mahal_kodu = data.get('mimari_mahal_kodu', '')
    location_name = data.get('location_name', '')
    phone_number = data.get('phone_number', '')
    if not location_code:
        return jsonify({"success": False, "error": "Mahal kodu gerekli!"}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO mahal_list (location_code, mimari_mahal_kodu, location_name, phone_number) VALUES (?, ?, ?, ?)", (location_code, mimari_mahal_kodu, location_name, phone_number))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@mahal_manager_bp.route('/update/<int:item_id>', methods=['PUT'])
@require_admin
def update_mahal(item_id):
    data = request.json
    location_code = data.get('location_code')
    mimari_mahal_kodu = data.get('mimari_mahal_kodu', '')
    location_name = data.get('location_name', '')
    phone_number = data.get('phone_number', '')
    if not location_code:
        return jsonify({"success": False, "error": "Mahal kodu gerekli!"}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE mahal_list SET location_code=?, mimari_mahal_kodu=?, location_name=?, phone_number=? WHERE id=?", (location_code, mimari_mahal_kodu, location_name, phone_number, item_id))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@mahal_manager_bp.route('/delete/<int:item_id>', methods=['DELETE'])
@require_admin
def delete_mahal(item_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM mahal_list WHERE id=?", (item_id,))
    conn.commit()
    conn.close()
    return jsonify({"success": True})
