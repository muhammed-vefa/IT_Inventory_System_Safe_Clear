from flask import Blueprint, jsonify, request
from monitoring.system_brain import check_system_health
from core.auth import require_auth

monitoring_manager_bp = Blueprint("monitoring_manager", __name__)

@monitoring_manager_bp.route("/health")
@require_auth
def system_health():
    # Detect base URL dynamically if possible, or use localhost:5000 as default
    base_url = request.host_url.rstrip('/')
    data = check_system_health(base_url)
    return jsonify(data)

@monitoring_manager_bp.route("/stats")
@require_auth
def system_stats():
    # Detailed stats for admin only
    base_url = request.host_url.rstrip('/')
    data = check_system_health(base_url)
    return jsonify(data)

from core.auth import require_admin
import subprocess
import os

@monitoring_manager_bp.route("/git_update", methods=['POST'])
@require_admin
def git_update():
    try:
        # Arka planda guncelle_ve_baslat.bat dosyasini calistir
        bat_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'guncelle_ve_baslat.bat')
        
        # Popen yerine Windows'ta direkt calistiran ve bagimsiz islem yaratan os.startfile kullaniyoruz
        os.startfile(bat_file)
        
        return jsonify({"success": True, "message": "Güncelleme başlatıldı. Sistem birkaç saniye içinde yeniden başlayacaktır..."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
