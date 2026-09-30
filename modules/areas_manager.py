from flask import Blueprint, jsonify, request
from core.database_sql import query_db
from core.auth import require_admin, require_editor

areas_manager_bp = Blueprint('areas_manager', __name__)

@areas_manager_bp.route('/get_all', methods=['GET'])
def get_all():
    try:
        results = query_db("SELECT * FROM shared_areas")
        if results:
            for row in results:
                uname = row.get('username') or row.get('user')
                row['username'] = uname
                row['user'] = uname
        return jsonify(results or [])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@areas_manager_bp.route('/add', methods=['POST'])
@require_editor
def add_area():
    try:
        data = request.json
        name = data.get('name')
        path = data.get('path')
        username = data.get('username') or data.get('user')
        password = data.get('password')
        
        if not name:
            return jsonify({"error": "Alan adi zorunludur"}), 400
            
        query_db("INSERT INTO shared_areas (name, path, username, password) VALUES (?,?,?,?)", 
                 (name, path, username, password))
        return jsonify({"success": True, "message": "Alan eklendi."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@areas_manager_bp.route('/update/<int:id>', methods=['PUT'])
@require_admin
def update_area(id):
    try:
        data = request.json
        username = data.get('username') or data.get('user')
        query_db("UPDATE shared_areas SET name=?, path=?, username=?, password=? WHERE id=?", 
                 (data.get('name'), data.get('path'), username, data.get('password'), id))
        return jsonify({"success": True, "message": "Alan guncellendi."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@areas_manager_bp.route('/delete/<int:id>', methods=['DELETE'])
@require_admin
def delete_area(id):
    try:
        query_db("DELETE FROM shared_areas WHERE id=?", (id,))
        return jsonify({"success": True, "message": "Alan silindi."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
