from flask import Blueprint, jsonify
areas_manager_bp = Blueprint('areas_manager', __name__)
@areas_manager_bp.route('/get_all', methods=['GET'])
def get_all(): return jsonify([])

bim_service_bp = Blueprint('bim_service', __name__)
document_service_bp = Blueprint('document_service', __name__)
google_sync_service_bp = Blueprint('google_sync_service', __name__)
keyos_service_bp = Blueprint('keyos_service', __name__)
logs_manager_bp = Blueprint('logs_manager', __name__)
mahal_manager_bp = Blueprint('mahal_manager', __name__)
printer_service_bp = Blueprint('printer_service', __name__)
service_manager_bp = Blueprint('service_manager', __name__)
