from flask import Blueprint, jsonify, request
from core.database_sql import get_db_connection
from core.auth import token_required
import datetime

inventory_manager_bp = Blueprint('inventory_manager', __name__)

@inventory_manager_bp.route('/get_all', methods=['GET'])
def get_all():
    conn = get_db_connection()
    if not conn: return jsonify([])
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM inventory ORDER BY pc_no")
    columns = [column[0] for column in cursor.description]
    results = [dict(zip(columns, row)) for row in cursor.fetchall()]
    conn.close()
    return jsonify(results)

@inventory_manager_bp.route('/stats', methods=['GET'])
def get_stats():
    conn = get_db_connection()
    if not conn: return jsonify({})
    cursor = conn.cursor()
    stats = {}
    
    cursor.execute("SELECT COUNT(*) FROM inventory WHERE windows=1")
    stats['windows'] = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM inventory WHERE keyos=1")
    stats['keyos'] = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM inventory WHERE sahada=1")
    stats['sahada'] = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM inventory WHERE type='PC'")
    stats['total_pc'] = cursor.fetchone()[0]
    
    conn.close()
    return jsonify(stats)

@inventory_manager_bp.route('/mahal_list', methods=['GET'])
def get_mahal_list():
    conn = get_db_connection()
    if not conn: return jsonify([])
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT mahal_kodu FROM inventory")
    results = [row[0] for row in cursor.fetchall() if row[0]]
    conn.close()
    return jsonify(results)

def _sync_peripherals():
    pass
