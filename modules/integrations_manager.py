from flask import Blueprint, request, jsonify
from core.database_sql import query_db

integrations_bp = Blueprint('integrations_bp', __name__)

@integrations_bp.route('/api/integrations', methods=['GET'])
def get_integrations():
    try:
        results = query_db("SELECT * FROM external_integrations WHERE is_deleted = 0 ORDER BY id DESC")
        return jsonify({"success": True, "data": results or []})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@integrations_bp.route('/api/integrations', methods=['POST'])
def add_integration():
    try:
        data = request.json
        site_code = data.get('site_code')
        base_url = data.get('base_url')
        
        if not site_code:
            return jsonify({"success": False, "message": "Site Code zorunludur."}), 400
            
        query = """
            INSERT INTO external_integrations 
            (site_code, base_url, auth_username, auth_password, api_key, settings_json, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        query_db(query, (
            site_code,
            base_url,
            data.get('auth_username'),
            data.get('auth_password'),
            data.get('api_key'),
            data.get('settings_json'),
            data.get('is_active', 1)
        ))
        
        return jsonify({"success": True, "message": "Entegrasyon eklendi."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@integrations_bp.route('/api/integrations/<int:id>', methods=['PUT'])
def update_integration(id):
    try:
        data = request.json
        query = """
            UPDATE external_integrations SET 
                site_code = ?,
                base_url = ?,
                auth_username = ?,
                auth_password = ?,
                api_key = ?,
                settings_json = ?,
                is_active = ?
            WHERE id = ?
        """
        query_db(query, (
            data.get('site_code'),
            data.get('base_url'),
            data.get('auth_username'),
            data.get('auth_password'),
            data.get('api_key'),
            data.get('settings_json'),
            data.get('is_active', 1),
            id
        ))
        
        return jsonify({"success": True, "message": "Entegrasyon güncellendi."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@integrations_bp.route('/api/integrations/<int:id>', methods=['DELETE'])
def delete_integration(id):
    try:
        query_db("UPDATE external_integrations SET is_deleted = 1 WHERE id = ?", (id,))
        return jsonify({"success": True, "message": "Entegrasyon silindi."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
