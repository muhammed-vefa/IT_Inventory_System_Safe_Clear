from flask import Blueprint, jsonify
bim_service_bp = Blueprint('bim_service', __name__)
@bim_service_bp.route('/test', methods=['GET'])
def test(): return jsonify({"status":"ok"})
