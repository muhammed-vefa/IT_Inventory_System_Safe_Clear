from flask import Blueprint, jsonify, request
from core.database_sql import get_db_connection
notes_manager_bp = Blueprint('notes_manager', __name__)
@notes_manager_bp.route('/get_all', methods=['GET'])
def get_all():
 # Bilgi Bankas kaytlar
 return jsonify([])
def sync_kb_from_excel_internal():
 return 0
