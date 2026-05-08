from flask import Blueprint, jsonify, request
from core.database_sql import query_db, get_db_connection, hash_password, verify_password
from core.extensions import limiter
from core.auth import require_auth, require_admin
import datetime

user_manager_bp = Blueprint('user_manager', __name__)


@user_manager_bp.route('/get_all', methods=['GET'])
@require_auth
def get_users():
    """Tüm kullanıcıları getirir (şifre hariç)."""
    try:
        users = query_db("SELECT id, username, display_name, role, permissions, created_at, last_login, last_activity, session_timeout FROM users")
        result = []
        for row in users:
            d = dict(row)
            # Tarihleri ISO formatına (Z ile) çevir ki browser UTC olduğunu anlasın
            for key in ['created_at', 'last_login', 'last_activity']:
                val = d.get(key)
                if val:
                    try:
                        if isinstance(val, (datetime.datetime, datetime.date)):
                            d[key] = val.isoformat() + "Z"
                        else:
                            # String ise (bazen pyodbc öyle döner), T harfi ve Z ekle
                            s_val = str(val).replace(" ", "T")
                            if "Z" not in s_val:
                                d[key] = s_val + "Z"
                    except Exception:
                        pass
            result.append(d)
        return jsonify(result)
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
        from main import get_now
        conn = get_db_connection()
        conn.execute("UPDATE users SET last_login = ?, last_activity = ? WHERE id = ?", (get_now(), get_now(), user_data['id']))
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
                "has_bim_pass": bool(user_data.get('bim_pass')),
                "keyos_user": user_data.get('keyos_user', ''),
                "keyos_pass": user_data.get('keyos_pass', ''),
                "has_keyos_pass": bool(user_data.get('keyos_pass')),
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
            (username, hash_password(password), display_name, role, data.get('permissions', '[]'))
        )
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "Kullanıcı başarıyla eklendi"})
    except Exception as e:
        print(f"Add User Error: {e}")
        return jsonify({"error": f"Kullanıcı eklenemedi: {str(e)}"}), 500


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
    user_id = request.current_user.get('user_id')
    if not user_id:
        return jsonify({"error": "Geçersiz oturum"}), 401
        
    try:
        conn = get_db_connection()
        # Sadece bu alanları güncelle (şifreler eğer boş değilse güncellenir)
        keyos_user = data.get('keyos_user')
        keyos_pass = data.get('keyos_pass')
        bim_user = data.get('bim_user')
        bim_pass = data.get('bim_pass')
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
        return jsonify({"success": True, "message": "Profil başarıyla güncellendi."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@user_manager_bp.route('/change_password', methods=['POST'])
@require_auth
def change_password():
    """Kullanıcının kendi şifresini değiştirmesini sağlar."""
    data = request.json
    user_id = request.current_user.get('user_id')
    old_password = data.get('old_password')
    new_password = data.get('new_password')
    
    if not user_id:
        return jsonify({"error": "Geçersiz oturum"}), 401
    if not old_password or not new_password:
        return jsonify({"error": "Eski şifre ve yeni şifre zorunludur"}), 400
        
    try:
        user = query_db("SELECT * FROM users WHERE id=?", (user_id,), one=True)
        if not user:
            return jsonify({"error": "Kullanıcı bulunamadı"}), 404
            
        user_data = dict(user)
        # Auth.py'den verify_password'ü kullandık
        if not verify_password(old_password, user_data['password_hash']):
            return jsonify({"error": "Mevcut şifreniz hatalı!"}), 400
            
        conn = get_db_connection()
        conn.execute("UPDATE users SET password_hash=? WHERE id=?", (hash_password(new_password), user_id))
        conn.commit()
        conn.close()
        
        return jsonify({"success": True, "message": "Şifreniz başarıyla değiştirildi."})
    except Exception as e:
        return jsonify({"error": f"Sistem hatası: {str(e)}"}), 500
