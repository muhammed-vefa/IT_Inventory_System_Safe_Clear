from flask import Blueprint, jsonify, request
from core.database_sql import get_db_connection
from core.auth import generate_token

user_manager_bp = Blueprint('user_manager', __name__)

@user_manager_bp.route('/login', methods=['POST'])
def login():
    data = request.json
    u, p = data.get('username'), data.get('password')
    conn = get_db_connection()
    if not conn: return jsonify({'success': False, 'error': 'DB Connection failed'}), 500
    
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, display_name, role FROM users WHERE username=? AND password=?", (u, p))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        u_dict = {'id': user[0], 'username': user[1], 'display_name': user[2], 'role': user[3]}
        token = generate_token(user[0], user[3])
        return jsonify({'success': True, 'user': u_dict, 'token': token})
    return jsonify({'success': False, 'error': 'Hatalı kullanıcı adı veya şifre'}), 401

@user_manager_bp.route('/get_all', methods=['GET'])
def get_all_users():
    conn = get_db_connection()
    if not conn: return jsonify([])
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, display_name, role FROM users")
    columns = [column[0] for column in cursor.description]
    results = [dict(zip(columns, row)) for row in cursor.fetchall()]
    conn.close()
    return jsonify(results)
