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

@monitoring_manager_bp.route("/git_update", methods=['POST'])
@require_admin
def git_update():
    return jsonify({'success': False, 'error': 'DISABLED', 'message': 'Site uzerinden guncelleme/komut calistirma devre disidir. Sadece rapor izleme desteklenir.'}), 410
