from flask import Blueprint, jsonify, request
from core.database_sql import query_db, get_db_connection, hash_password, verify_password
from core.extensions import limiter
from core.auth import require_auth, require_admin
import datetime

user_manager_bp = Blueprint('user_manager', __name__)


@user_manager_bp.route('/get_all', methods=['GET'])
def get_users():
    """Tüm kullanıcıları getirir (şifre hariç)."""
    try:
        users = query_db("SELECT id, username, display_name, role, permissions, created_at, last_login, session_timeout FROM users")
        return jsonify([dict(row) for row in users])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@user_manager_bp.route('/login', methods=['POST'])
@limiter.limit("5 per minute")
def login():
    """Kullanıcı giriş doğrulama + JWT Token üretimi."""
    from core.auth import create_token
    data = request.json
    username = data.get('username', '')
    password = data.get('password', '')
    
    if not username or not password:
        return jsonify({"error": "Kullanıcı adı ve şifre gerekli"}), 400
    
    try:
        user = query_db("SELECT * FROM users WHERE LOWER(username)=?", (username.lower(),), one=True)
        if not user:
            return jsonify({"error": "Kullanıcı bulunamadı"}), 401
        
        user_data = dict(user)
        if not verify_password(password, user_data['password_hash']):
            return jsonify({"error": "Şifre yanlış"}), 401
        
        # Son giriş zamanını güncelle
        conn = get_db_connection()
        conn.execute("UPDATE users SET last_login = ? WHERE id = ?", (datetime.datetime.now(), user_data['id']))
        conn.commit()
        conn.close()
        
        # JWT Token oluştur
        token = create_token(user_data)
        
        return jsonify({
            "message": "Giriş başarılı",
            "token": token,
            "user": {
                "id": user_data['id'],
                "username": user_data['username'],
                "display_name": user_data['display_name'],
                "role": user_data['role'],
                "permissions": user_data.get('permissions'),
                "bim_user": user_data.get('bim_user', ''),
                "bim_pass": user_data.get('bim_pass', ''),
                "keyos_user": user_data.get('keyos_user', ''),
                "keyos_pass": user_data.get('keyos_pass', ''),
                "magicinfo_user": user_data.get('magicinfo_user', ''),
                "magicinfo_pass": user_data.get('magicinfo_pass', ''),
                "session_timeout": user_data.get('session_timeout', 30)
            }
        })
    except Exception as e:
        print(f"Login Error: {e}")
        return jsonify({"error": "Giriş işlemi sırasında hata oluştu"}), 500


@user_manager_bp.route('/add', methods=['POST'])
@require_admin
def add_user():
    """Yeni kullanıcı ekler (sadece admin)."""
    data = request.json
    username = data.get('username', '')
    password = data.get('password', '')
    display_name = data.get('display_name', '')
    role = data.get('role', 'EDITOR')
    
    if not username or not password or not display_name:
        return jsonify({"error": "Tüm alanlar zorunludur"}), 400
    
    try:
        existing = query_db("SELECT id FROM users WHERE username=?", (username,), one=True)
        if existing:
            return jsonify({"error": "Bu kullanıcı adı zaten mevcut"}), 409
        
        conn = get_db_connection()
        conn.execute(
            "INSERT INTO users (username, password_hash, display_name, role, permissions) VALUES (?,?,?,?,?)",
            (username, hash_password(password), display_name, role, data.get('permissions'))
        )
        conn.commit()
        conn.close()
        return jsonify({"message": "Kullanıcı eklendi"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@user_manager_bp.route('/update/<int:user_id>', methods=['PUT'])
@require_admin
def update_user(user_id):
    """Kullanıcı bilgilerini günceller."""
    data = request.json
    try:
        conn = get_db_connection()
        
        # Şifre değiştirilecekse
        if data.get('password'):
            conn.execute(
                "UPDATE users SET display_name=?, role=?, permissions=?, password_hash=? WHERE id=?",
                (data.get('display_name'), data.get('role'), data.get('permissions'), hash_password(data['password']), user_id)
            )
        else:
            conn.execute(
                "UPDATE users SET display_name=?, role=?, permissions=? WHERE id=?",
                (data.get('display_name'), data.get('role'), data.get('permissions'), user_id)
            )
        
        conn.commit()
        conn.close()
        return jsonify({"message": "Kullanıcı güncellendi"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@user_manager_bp.route('/delete/<int:user_id>', methods=['DELETE'])
@require_admin
def delete_user(user_id):
    """Kullanıcıyı siler."""
    try:
        # Admin kendini silemesin
        user = query_db("SELECT * FROM users WHERE id=?", (user_id,), one=True)
        if not user:
            return jsonify({"error": "Kullanıcı bulunamadı"}), 404
        
        # En az 1 admin kalmalı
        user_data = dict(user)
        if user_data['role'] == 'ADMIN':
            admin_count = query_db("SELECT COUNT(*) as cnt FROM users WHERE role='ADMIN'", one=True)
            if dict(admin_count)['cnt'] <= 1:
                return jsonify({"error": "Son admin kullanıcı silinemez"}), 400
        
        conn = get_db_connection()
        conn.execute("DELETE FROM users WHERE id=?", (user_id,))
        conn.commit()
        conn.close()
        return jsonify({"message": "Kullanıcı silindi"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
@user_manager_bp.route('/update_profile', methods=['POST'])
@require_auth
def update_profile():
    """Kullanıcının kendi KeyOS ve BIM bilgilerini güncellemesini sağlar."""
    data = request.json
    user_id = data.get('id')
    if not user_id:
        return jsonify({"error": "Kullanıcı ID bulunamadı"}), 400
        
    try:
        conn = get_db_connection()
        # Sadece bu alanları güncelle (şifreler eğer boş değilse güncellenir)
        keyos_user = data.get('keyos_user')
        keyos_pass = data.get('keyos_pass')
        bim_user = data.get('bim_user')
        bim_pass = data.get('bim_pass')
        magicinfo_user = data.get('magicinfo_user')
        magicinfo_pass = data.get('magicinfo_pass')
        session_timeout = data.get('session_timeout')
        
        query = "UPDATE users SET "
        params = []
        updates = []
        
        if keyos_user is not None:
            updates.append("keyos_user = ?")
            params.append(keyos_user)
        if keyos_pass: # Sadece doluysa güncelle
            updates.append("keyos_pass = ?")
            params.append(keyos_pass)
        if bim_user is not None:
            updates.append("bim_user = ?")
            params.append(bim_user)
        if bim_pass:
            updates.append("bim_pass = ?")
            params.append(bim_pass)
        if magicinfo_user is not None:
            updates.append("magicinfo_user = ?")
            params.append(magicinfo_user)
        if magicinfo_pass:
            updates.append("magicinfo_pass = ?")
            params.append(magicinfo_pass)
        if session_timeout is not None:
            updates.append("session_timeout = ?")
            params.append(session_timeout)
            
        if not updates:
            return jsonify({"message": "Güncellenecek veri yok"})
            
        query += ", ".join(updates) + " WHERE id = ?"
        params.append(user_id)
        
        conn.execute(query, params)
        conn.commit()
        conn.close()
        return jsonify({"message": "Profil başarıyla güncellendi."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
