from flask import Blueprint, jsonify
logs_manager_bp = Blueprint('logs_manager', __name__)
@logs_manager_bp.route('/get_all', methods=['GET'])
def get_all(): return jsonify([])
