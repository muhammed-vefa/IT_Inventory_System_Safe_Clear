from flask import Blueprint, jsonify
keyos_service_bp = Blueprint('keyos_service', __name__)
@keyos_service_bp.route('/test', methods=['GET'])
def test(): return jsonify({"status":"ok"})
