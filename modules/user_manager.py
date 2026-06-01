from flask import Blueprint, jsonify, request
from core.database_sql import get_db_connection
from core.auth import generate_token, require_auth, require_admin

from werkzeug.security import generate_password_hash, check_password_hash

from core.limiter import limiter

user_manager_bp = Blueprint('user_manager', __name__)

@user_manager_bp.route('/login', methods=['POST'])
@limiter.limit("5 per minute")
def login():
    try:
        data = request.json
        u, p = data.get('username'), data.get('password')
        conn = get_db_connection()
        if not conn: return jsonify({'success': False, 'error': 'DB Connection failed'}), 500
        # SQL Server Collation ve Türkçe karakter sorunlarını (I/i/ı/İ) kökten çözmek için:
        # Tüm kullanıcıları çekip Python üzerinde normalize ederek eşleştiriyoruz.
        # Kullanıcı tablosu küçük olduğu için performans sorunu yaratmaz.
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, role, session_timeout, password_hash, display_name, keyos_user, keyos_pass, bim_user, bim_pass, permissions FROM users")
        all_users = cursor.fetchall()
        conn.close()
        
        target_u = u.strip().replace('ı', 'i').replace('I', 'i').replace('İ', 'i').lower()
        user_row = None
        
        for row in all_users:
            db_u = str(row[1]).strip().replace('ı', 'i').replace('I', 'i').replace('İ', 'i').lower()
            if db_u == target_u:
                user_row = row
                break
        
        if user_row:
            u_id, u_name, u_role, u_timeout, db_hash, disp_name, keyos_u, keyos_p_enc, bim_u, bim_p_enc, u_perms = user_row
            
            if db_hash and check_password_hash(db_hash, p):
                from core.encryption import decrypt_password
                from core.auth import create_token, create_refresh_token
                from flask import make_response
                
                # NULL NORMALIZATION (AŞAMA 2)
                user_normalized = {
                    "id": int(u_id or 0),
                    "username": str(u_name or ""),
                    "display_name": str(disp_name or u_name or ""),
                    "role": str(u_role or "user"),
                    "permissions": str(u_perms or "[]"),
                    "bim_user": str(bim_u or ""),
                    "bim_pass": str(bim_p_enc or ""),
                    "keyos_user": str(keyos_u or ""),
                    "keyos_pass": str(keyos_p_enc or ""),
                    "session_timeout": int(u_timeout or 30)
                }
                
                access_token = create_token(user_normalized)
                refresh_token = create_refresh_token(u_id)
                
                # Activity log
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO user_activity_log (user_id, username, action, details, client_ip, user_agent) VALUES (?, ?, ?, ?, ?, ?)",
                    (u_id, u_name, 'LOGIN', 'Giriş Başarılı', request.remote_addr, request.headers.get('User-Agent'))
                )
                cursor.execute("UPDATE users SET last_login = GETDATE() WHERE id = ?", (u_id,))
                conn.commit()
                conn.close()

                # STANDART RESPONSE (AŞAMA 1)
                final_resp = {
                    "success": True,
                    "user": user_normalized
                }
                response = make_response(jsonify(final_resp))
                
                # Access Token Cookie (15m)
                response.set_cookie('access_token', access_token, httponly=True, samesite='Lax', max_age=900)
                # Refresh Token Cookie (7d)
                response.set_cookie('refresh_token', refresh_token, httponly=True, samesite='Lax', max_age=604800)
                
                return response
        
        # BAŞARISIZ LOGIN (AŞAMA 1)
        print(f"[LOGIN FAIL] Username: '{u}', UserFound: {bool(user_row)}")
        return jsonify({
            "success": False, 
            "message": "invalid_credentials",
            "user": None
        }), 401
    except Exception as e:
        import traceback
        print(f"[LOGIN ERROR] {traceback.format_exc()}")
        return jsonify({
            "success": False, 
            "error": f"Sistem Hatası: {str(e)}",
            "user": None
        }), 500

@user_manager_bp.route('/logout', methods=['POST'])
def logout():
    """Oturumu kapatır ve cookie'leri temizler."""
    from flask import make_response
    response = make_response(jsonify({'success': True}))
    response.set_cookie('access_token', '', expires=0)
    response.set_cookie('refresh_token', '', expires=0)
    return response

@user_manager_bp.route('/refresh', methods=['POST'])
def refresh():
    try:
        from flask import make_response
        from core.auth import create_token
        
        refresh_token = request.cookies.get('refresh_token')
        if not refresh_token:
            return jsonify({"error": "Refresh token missing"}), 401
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verify the refresh token exists, is not expired, and is not revoked
        cursor.execute("""
            SELECT user_id FROM refresh_tokens 
            WHERE token = ? AND expires_at > GETDATE() AND (revoked = 0 OR revoked IS NULL)
        """, (refresh_token,))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return jsonify({"error": "Invalid or expired refresh token"}), 401
            
        user_id = row[0]
        
        # Get user info to bake into the new token
        cursor.execute("""
            SELECT id, username, role, display_name, session_timeout, permissions 
            FROM users 
            WHERE id = ? AND is_deleted = 0
        """, (user_id,))
        user_row = cursor.fetchone()
        
        if not user_row:
            conn.close()
            return jsonify({"error": "User not found"}), 401
            
        u_id, u_name, u_role, disp_name, u_timeout, u_perms = user_row
        
        user_normalized = {
            "id": int(u_id or 0),
            "username": str(u_name or ""),
            "display_name": str(disp_name or u_name or ""),
            "role": str(u_role or "user"),
            "permissions": str(u_perms or "[]"),
            "session_timeout": int(u_timeout or 30)
        }
        
        # Generate new access token
        access_token = create_token(user_normalized)
        
        response = make_response(jsonify({"success": True}))
        # Set new access token cookie
        response.set_cookie('access_token', access_token, httponly=True, samesite='Lax', max_age=900)
        
        conn.close()
        return response
        
    except Exception as e:
        print(f"[REFRESH ERROR] {e}")
        return jsonify({"error": str(e)}), 500



@user_manager_bp.route('/get_all', methods=['GET'])
def get_all_users():
    try:
        from core.database_sql import query_db
        # Dinamik olarak kullanıcıları çekerken hata vermemesi için
        results = query_db("SELECT * FROM users")
        if results:
            # Sadece güvenli ve frontend'in ihtiyaç duyduğu alanları döndür
            safe_results = []
            for r in results:
                safe_results.append({
                    "id": r.get("id"),
                    "username": r.get("username"),
                    "display_name": r.get("display_name"),
                    "role": r.get("role", "VIEWER"),
                    "keyos_user": r.get("keyos_user"),
                    "bim_user": r.get("bim_user"),
                    "session_timeout": r.get("session_timeout", 30),
                    "created_at": r.get("created_at"),
                    "last_login": r.get("last_login"),
                    "permissions": r.get("permissions")
                })
            return jsonify(safe_results)
        return jsonify([])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@user_manager_bp.route('/change_password', methods=['POST'])
@require_auth
def change_password():
    try:
        data = request.json
        old_password = data.get('old_password')
        new_password = data.get('new_password')
        user_id = request.current_user.get('user_id')

        if not old_password or not new_password:
            return jsonify({'error': 'Eski ve yeni şifre gereklidir'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash FROM users WHERE id=?", (user_id,))
        row = cursor.fetchone()

        if not row or not check_password_hash(row[0], old_password):
            conn.close()
            return jsonify({'error': 'Mevcut şifre hatalı'}), 401

        # Yeni sifreyi kriptolayarak kaydediyoruz
        hashed_pw = generate_password_hash(new_password)
        cursor.execute("UPDATE users SET password_hash=? WHERE id=?", (hashed_pw, user_id))
        conn.commit()
        conn.close()

        return jsonify({'success': True, 'message': 'Şifre başarıyla güncellendi'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@user_manager_bp.route('/add', methods=['POST'])
@require_admin
def add_user():
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')
        display_name = data.get('display_name')
        role = data.get('role', 'VIEWER')
        permissions = data.get('permissions')

        if not username or not password:
            return jsonify({'error': 'Kullanıcı adı ve şifre zorunludur'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Sifreyi kriptola
        hashed = generate_password_hash(password)
        
        # Mükerrer kontrolü
        cursor.execute("SELECT id FROM users WHERE LOWER(username) = ?", (username.lower(),))
        if cursor.fetchone():
            conn.close()
            return jsonify({'error': 'Bu kullanıcı adı zaten mevcut'}), 400
        
        cursor.execute("""
            INSERT INTO users (username, password_hash, display_name, role, permissions) 
            VALUES (?, ?, ?, ?, ?)
        """, (username, hashed, display_name, role, permissions))
        
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@user_manager_bp.route('/update/<int:user_id>', methods=['PUT'])
@require_admin
def update_user(user_id):
    try:
        data = request.json
        display_name = data.get('display_name')
        role = data.get('role')
        password = data.get('password')
        permissions = data.get('permissions')

        conn = get_db_connection()
        cursor = conn.cursor()
        
        if password:
            # Sifre deisiyorsa kriptola
            hashed = generate_password_hash(password)
            cursor.execute("""
                UPDATE users SET display_name=?, role=?, password_hash=?, permissions=? WHERE id=?
            """, (display_name, role, hashed, permissions, user_id))
        else:
            cursor.execute("""
                UPDATE users SET display_name=?, role=?, permissions=? WHERE id=?
            """, (display_name, role, permissions, user_id))
            
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@user_manager_bp.route('/update_profile', methods=['POST'])
@require_auth
def update_profile():
    try:
        data = request.json
        user_id = request.current_user.get('user_id')
        
        # Sadece giriş yapan kullanıcı kendi profilini güncelleyebilir 
        # (Frontend data'daki id ile token'daki id'yi karşılaştırabiliriz ama request.current_user daha güvenli)
        
        keyos_user = data.get('keyos_user')
        keyos_pass = data.get('keyos_pass')
        bim_user = data.get('bim_user')
        bim_pass = data.get('bim_pass')
        session_timeout = data.get('session_timeout', 60)

        from core.encryption import encrypt_password
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Servis şifrelerini SİFRELEYEREK kaydediyoruz (Hash değil!)
        enc_keyos = encrypt_password(keyos_pass) if keyos_pass else None
        enc_bim = encrypt_password(bim_pass) if bim_pass else None

        if enc_keyos and enc_bim:
            cursor.execute("""
                UPDATE users 
                SET keyos_user=?, keyos_pass=?, bim_user=?, bim_pass=?, session_timeout=? 
                WHERE id=?
            """, (keyos_user, enc_keyos, bim_user, enc_bim, session_timeout, user_id))
        elif enc_keyos:
            cursor.execute("""
                UPDATE users 
                SET keyos_user=?, keyos_pass=?, bim_user=?, session_timeout=? 
                WHERE id=?
            """, (keyos_user, enc_keyos, bim_user, session_timeout, user_id))
        elif enc_bim:
            cursor.execute("""
                UPDATE users 
                SET keyos_user=?, bim_user=?, bim_pass=?, session_timeout=? 
                WHERE id=?
            """, (keyos_user, bim_user, enc_bim, session_timeout, user_id))
        else:
            cursor.execute("""
                UPDATE users 
                SET keyos_user=?, bim_user=?, session_timeout=? 
                WHERE id=?
            """, (keyos_user, bim_user, session_timeout, user_id))
            
        conn.commit()
        conn.close()

        return jsonify({'success': True, 'message': 'Profil başarıyla güncellendi'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@user_manager_bp.route('/delete/<int:user_id>', methods=['DELETE'])
@require_admin
def delete_user(user_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Kullanıcı silindi'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
