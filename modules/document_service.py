from flask import Blueprint, jsonify, send_from_directory
import os
import datetime

document_service_bp = Blueprint('document_service', __name__)

# downloads klasorunun tam yolu
BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
# Gerekli Indirmeler icin ana dizin (Masaüstü vs için klasör adı)
DL_DIR = os.path.join(BASE_DIR, "bat_uygulama")

@document_service_bp.route('/list', methods=['GET'])
def list_files():
    try:
        if not os.path.exists(DL_DIR):
            os.makedirs(DL_DIR, exist_ok=True)
            
        files = []
        for f in os.listdir(DL_DIR):
            f_path = os.path.join(DL_DIR, f)
            if os.path.isfile(f_path):
                stats = os.stat(f_path)
                files.append({
                    "name": f,
                    "size": f"{round(stats.st_size / 1024, 2)} KB",
                    "date": datetime.datetime.fromtimestamp(stats.st_mtime).strftime("%Y-%m-%d %H:%M")
                })
        return jsonify({"success": True, "files": files})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@document_service_bp.route('/get/<filename>', methods=['GET'])
def get_file(filename):
    try:
        return send_from_directory(DL_DIR, filename, as_attachment=True)
    except Exception as e:
        return jsonify({"success": False, "error": "Dosya bulunamadi"}), 404
