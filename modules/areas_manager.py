from flask import Blueprint, jsonify, request
from core.database_sql import query_db, get_db_connection
from core.auth import require_auth, require_editor, require_admin

areas_manager_bp = Blueprint('areas_manager', __name__)

@areas_manager_bp.route('/get_all', methods=['GET'])
@require_auth
def get_areas():
    """Tüm ortak ağ alanlarını getirir."""
    try:
        items = query_db("SELECT * FROM shared_areas")
        result = []
        for row in items:
            d = dict(row)
            # Şifreyi maskele — düzenleme formunda ayrıca çekilir
            if d.get('password'):
                d['password'] = '••••••'
            result.append(d)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@areas_manager_bp.route('/search', methods=['GET'])
@require_auth
def search_areas():
    q = request.args.get('q', '')
    try:
        items = query_db("SELECT * FROM shared_areas WHERE name LIKE ? OR path LIKE ?", ('%'+q+'%', '%'+q+'%'))
        return jsonify([dict(row) for row in items])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@areas_manager_bp.route('/add', methods=['POST'])
@require_editor
def add_area():
    data = request.json
    try:
        conn = get_db_connection()
        conn.execute("INSERT INTO shared_areas (name, path, [user], password) VALUES (?, ?, ?, ?)",
            (data.get('name'), data.get('path'), data.get('user'), data.get('password')))
        conn.commit()
        return jsonify({"message": "Ortak alan eklendi"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@areas_manager_bp.route('/update/<int:id>', methods=['PUT'])
@require_editor
def update_area(id):
    data = request.json
    try:
        conn = get_db_connection()
        conn.execute("UPDATE shared_areas SET name=?, path=?, [user]=?, password=? WHERE id=?",
            (data.get('name'), data.get('path'), data.get('user'), data.get('password'), id))
        conn.commit()
        return jsonify({"message": "Ortak alan güncellendi"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
@areas_manager_bp.route('/delete/<int:id>', methods=['DELETE'])
@require_admin
def delete_area(id):
    try:
        conn = get_db_connection()
        conn.execute("DELETE FROM shared_areas WHERE id=?", (id,))
        conn.commit()
        return jsonify({"message": "Ortak alan silindi"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
