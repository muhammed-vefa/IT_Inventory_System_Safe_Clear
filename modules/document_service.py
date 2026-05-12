from flask import Blueprint, jsonify
document_service_bp = Blueprint('document_service', __name__)
@document_service_bp.route('/test', methods=['GET'])
def test(): return jsonify({"status":"ok"})
