from flask import Blueprint, jsonify, send_file, request
from core.auth import require_auth
import os

bat_manager_bp = Blueprint('bat_manager', __name__)
BAT_DIR = r"C:\WebApps\IT_Inventory_System\bat_uygulama"

@bat_manager_bp.route('/list', methods=['GET'])
@require_auth
def list_bat_files():
    try:
        if not os.path.exists(BAT_DIR):
            os.makedirs(BAT_DIR, exist_ok=True)
            
        files = []
        for file in os.listdir(BAT_DIR):
            if file.endswith('.bat') or file.endswith('.exe') or file.endswith('.zip') or file.endswith('.msi'):
                file_path = os.path.join(BAT_DIR, file)
                size = os.path.getsize(file_path)
                files.append({
                    "name": file,
                    "size": f"{size / 1024:.1f} KB" if size < 1024 * 1024 else f"{size / (1024 * 1024):.1f} MB"
                })
        return jsonify(files)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bat_manager_bp.route('/download/<filename>', methods=['GET'])
@require_auth
def download_bat_file(filename):
    try:
        # Prevent directory traversal
        safe_filename = os.path.basename(filename)
        file_path = os.path.join(BAT_DIR, safe_filename)
        
        if not os.path.exists(file_path):
            return jsonify({"error": "Dosya bulunamadi."}), 404
            
        return send_file(file_path, as_attachment=True)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
