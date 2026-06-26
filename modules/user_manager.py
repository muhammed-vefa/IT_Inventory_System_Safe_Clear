from flask import Blueprint, jsonify, request
from core.database_sql import get_db_connection
from core.auth import generate_token, require_auth, require_admin

from werkzeug.security import generate_password_hash, check_password_hash

from core.limiter import limiter

user_manager_bp = Blueprint('user_manager', __name__)

def get_client_ip_candidates():
    """Proxy arkasında güvenilir IP eşleşmesi için olası IP adaylarını döndürür."""
    candidates = []
    for header in ('X-Forwarded-For', 'X-Real-IP', 'CF-Connecting-IP'):
        value = request.headers.get(header)
        if value:
            for part in str(value).split(','):
                ip = part.strip()
                if ip and ip not in candidates:
                    candidates.append(ip)
    remote = request.remote_addr
    if remote and remote not in candidates:
        candidates.append(remote)
    return candidates or ['127.0.0.1']

def is_trusted_client_ip(trusted_ips):
    trusted_list = [ip.strip() for ip in str(trusted_ips or '').split(',') if ip.strip()]
    candidates = get_client_ip_candidates()
    return any(ip in trusted_list for ip in candidates), candidates[0]


@user_manager_bp.route('/login', methods=['POST'])
# @limiter.limit("5 per minute")  # Geçici olarak devre dışı bırakıldı
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
        cursor.execute("SELECT id, username, role, session_timeout, password_hash, display_name, keyos_user, keyos_pass, bim_user, bim_pass, permissions, trusted_ips FROM users")
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
            u_id, u_name, u_role, u_timeout, db_hash, disp_name, keyos_u, keyos_p_enc, bim_u, bim_p_enc, u_perms, trusted_ips = user_row
            
            if db_hash and check_password_hash(db_hash, p):
                from core.encryption import decrypt_password
                from core.auth import create_token, create_refresh_token
                from flask import make_response
                import uuid
                
                decrypted_bim = decrypt_password(bim_p_enc) if bim_p_enc else ""
                decrypted_keyos = decrypt_password(keyos_p_enc) if keyos_p_enc else ""

                # Trusted IP Kontrolü (Aşama 1: 1 Yıl Süre)
                is_trusted, client_ip = is_trusted_client_ip(trusted_ips)
                        
                if is_trusted:
                    expiry_hours = 8760
                else:
                    if u_timeout and int(u_timeout) > 0:
                        expiry_hours = int(u_timeout) / 60.0
                    elif u_timeout == 0:
                        expiry_hours = 8760
                    else:
                        expiry_hours = 12

                import uuid
                new_session_token = uuid.uuid4().hex

                user_normalized = {
                    "id": int(u_id or 0),
                    "username": str(u_name or ""),
                    "display_name": str(disp_name or u_name or ""),
                    "role": str(u_role or "user"),
                    "permissions": str(u_perms or "[]"),
                    "bim_user": str(bim_u or ""),
                    "bim_pass": "********" if decrypted_bim else "",
                    "keyos_user": str(keyos_u or ""),
                    "keyos_pass": "********" if decrypted_keyos else "",
                    "session_timeout": int(u_timeout) if u_timeout is not None and str(u_timeout).strip() != "" else 5,
                    "trusted_ips": str(trusted_ips or ""),
                    "is_trusted": bool(is_trusted)
                }

                access_token = create_token(user_normalized, expiry_hours=expiry_hours, session_token=new_session_token)
                refresh_token = create_refresh_token(u_id, client_ip=client_ip, user_agent=request.headers.get('User-Agent'), expiry_days=365 if is_trusted else 7)
                
                # Activity log & DB Session Update
                conn = get_db_connection()
                cursor = conn.cursor()
                
                # Herhangi bir girişte, eğer önceki oturum "Güvenilmez" ise onu temizler (Eski cihazdaki açık oturumu kapatır)
                cursor.execute("DELETE FROM user_sessions WHERE user_id = ? AND is_trusted = 0", (u_id,))
                
                user_agent = request.headers.get('User-Agent', '')[:250]
                cursor.execute("""
                    INSERT INTO user_sessions (user_id, session_token, ip_address, user_agent, is_trusted) 
                    VALUES (?, ?, ?, ?, ?)
                """, (u_id, new_session_token, client_ip, user_agent, 1 if is_trusted else 0))
                
                cursor.execute("UPDATE users SET last_login = GETDATE() WHERE id = ?", (u_id,))
                cursor.execute("INSERT INTO user_activity_log (user_id, username, action, details, client_ip, user_agent) VALUES (?, ?, ?, ?, ?, ?)",
                    (u_id, u_name, 'LOGIN', 'Giriş Başarılı', client_ip, request.headers.get('User-Agent'))
                )
                conn.commit()
                conn.close()
 
                # STANDART RESPONSE (AŞAMA 1)
                final_resp = {
                    "success": True,
                    "user": user_normalized,
                    "token": access_token
                }
                response = make_response(jsonify(final_resp))
                
                # Dinamik Cookie Max-Age hesaplama
                cookie_max_age = int(expiry_hours * 3600)
                
                # Access Token Cookie (Dinamik Süre)
                response.set_cookie('access_token', access_token, httponly=True, samesite='Lax', max_age=cookie_max_age)
                # Refresh Token Cookie (7d veya 1y)
                response.set_cookie('refresh_token', refresh_token, httponly=True, samesite='Lax', max_age=604800 if not is_trusted else 31536000)
                
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
    try:
        from core.auth import decode_token
        token = request.cookies.get('access_token')
        if token:
            payload = decode_token(token)
            if payload:
                user_id = payload.get('user_id')
                session_token = payload.get('session_token')
                if user_id and session_token:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM user_sessions WHERE user_id = ? AND CONVERT(NVARCHAR(255), session_token) = CONVERT(NVARCHAR(255), ?)", (user_id, session_token))
                    conn.commit()
                    conn.close()
    except Exception as e:
        print(f"[LOGOUT DB ERROR] {e}")
        
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
            SELECT id, username, role, display_name, session_timeout, permissions, trusted_ips 
            FROM users 
            WHERE id = ? AND is_deleted = 0
        """, (user_id,))
        user_row = cursor.fetchone()
        
        if not user_row:
            conn.close()
            return jsonify({"error": "User not found"}), 401
            
        u_id, u_name, u_role, disp_name, u_timeout, u_perms, trusted_ips = user_row
        
        is_trusted, client_ip = is_trusted_client_ip(trusted_ips)

        user_normalized = {
            "id": int(u_id or 0),
            "username": str(u_name or ""),
            "display_name": str(disp_name or u_name or ""),
            "role": str(u_role or "user"),
            "permissions": str(u_perms or "[]"),
            "session_timeout": int(u_timeout or 30),
            "trusted_ips": str(trusted_ips or ""),
            "is_trusted": bool(is_trusted)
        }
        
        if is_trusted:
            expiry_hours = 8760
            cookie_max_age = 31536000
        else:
            expiry_hours = 12
            cookie_max_age = int(expiry_hours * 3600)
        
        # Generate new access token
        access_token = create_token(user_normalized, expiry_hours=expiry_hours)
        
        response = make_response(jsonify({
            "success": True,
            "token": access_token
        }))
        # Set new access token cookie
        response.set_cookie('access_token', access_token, httponly=True, samesite='Lax', max_age=cookie_max_age)
        
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
        if keyos_pass == '********': keyos_pass = None
        
        bim_user = data.get('bim_user')
        bim_pass = data.get('bim_pass')
        if bim_pass == '********': bim_pass = None
        
        session_timeout = data.get('session_timeout', 60)
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
            
        if 'trusted_ips' in data:
            trusted_ips = data.get('trusted_ips', '')
            if trusted_ips:
                ip_list = [ip.strip() for ip in trusted_ips.split(',') if ip.strip()]
                if len(ip_list) > 3:
                    ip_list = ip_list[:3]
                trusted_ips = ','.join(ip_list)
            cursor.execute("UPDATE users SET trusted_ips=? WHERE id=?", (trusted_ips, user_id))

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

@user_manager_bp.route('/sessions', methods=['GET'])
@require_auth
def get_user_sessions():
    try:
        user_id = request.current_user.get('user_id')
        current_session_token = request.current_user.get('session_token')

        conn = get_db_connection()
        cursor = conn.cursor()

        # SQL Server ntext alanlarında SQL gruplama/karşılaştırma hatası olmaması için
        # session_token CONVERT edilir ve IP bazlı tekilleştirme Python tarafında yapılır.
        cursor.execute("""
            SELECT
                CONVERT(NVARCHAR(255), session_token) AS session_token,
                ip_address,
                user_agent,
                is_trusted,
                created_at,
                last_activity,
                id
            FROM user_sessions
            WHERE user_id = ?
            ORDER BY ISNULL(last_activity, created_at) DESC
        """, (user_id,))
        rows = cursor.fetchall()

        ip_map = {}
        for row in rows:
            ip = row[1] or '-'
            last_activity = row[5] or row[4]
            old_row = ip_map.get(ip)
            old_last = (old_row[5] or old_row[4]) if old_row else None
            if old_row is None or (last_activity and (old_last is None or last_activity > old_last)):
                ip_map[ip] = row

        unique_rows = list(ip_map.values())
        conn.close()

        sessions = []
        for row in unique_rows:
            token_value = str(row[0] or '')
            sessions.append({
                "token": token_value,
                "ip_address": row[1],
                "client_ip": row[1],
                "user_agent": row[2],
                "is_trusted": bool(row[3]),
                "created_at": row[4].strftime('%Y-%m-%d %H:%M:%S') if row[4] else None,
                "last_activity": row[5].strftime('%Y-%m-%d %H:%M:%S') if row[5] else None,
                "is_current": (token_value == str(current_session_token or '')),
                "id": row[6]
            })

        return jsonify({'success': True, 'sessions': sessions})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@user_manager_bp.route('/trust_ip', methods=['POST'])
@require_auth
def trust_ip():
    try:
        user_id = request.current_user.get('user_id')
        data = request.json or {}
        ip_to_trust = data.get('ip_address')
        
        if not ip_to_trust:
            return jsonify({'success': False, 'error': 'IP adresi gereklidir'}), 400
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Mevcut trusted_ips bilgisini al
        cursor.execute("SELECT trusted_ips FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        
        trusted_ips_str = row[0] if row and row[0] else ""
        ip_list = [ip.strip() for ip in trusted_ips_str.split(',') if ip.strip()]
        
        if ip_to_trust not in ip_list:
            if len(ip_list) >= 3:
                # Eger 3 taneyse, en eskisini cikaralim (listeden ilkini)
                ip_list.pop(0)
            ip_list.append(ip_to_trust)
            
            new_trusted_ips = ','.join(ip_list)
            cursor.execute("UPDATE users SET trusted_ips = ? WHERE id = ?", (new_trusted_ips, user_id))
            
            # Ayni zamanda user_sessions tablosunda bu IP'yi is_trusted = 1 yapalim
            cursor.execute("UPDATE user_sessions SET is_trusted = 1 WHERE user_id = ? AND ip_address = ?", (user_id, ip_to_trust))
            conn.commit()
            
        conn.close()
        return jsonify({'success': True, 'message': f'{ip_to_trust} gvenli IP olarak eklendi.'})
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@user_manager_bp.route('/sessions/revoke', methods=['POST'])
@require_auth
def revoke_session():
    try:
        user_id = request.current_user.get('user_id')
        current_session_token = request.current_user.get('session_token')
        
        data = request.json or {}
        session_id = data.get('session_id')
        
        if not session_id:
            return jsonify({'success': False, 'error': 'session_id gereklidir'}), 400
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # ID bazlı kontrol edelim:
        cursor.execute("SELECT session_token FROM user_sessions WHERE id = ? AND user_id = ?", (session_id, user_id))
        row = cursor.fetchone()
        
        if row:
            sess_token = row[0]
            if sess_token == current_session_token:
                conn.close()
                return jsonify({'success': False, 'error': 'Mevcut oturumunuzu buradan silemezsiniz, sistemden cikis yapin.'}), 400
            
            # ID bazli silmek yerine, eger IP bazli grupladiysak, o IP'deki tum oturumlari silmek daha saglikli
            cursor.execute("SELECT ip_address FROM user_sessions WHERE id = ?", (session_id,))
            ip_row = cursor.fetchone()
            if ip_row:
                ip_addr = ip_row[0]
                cursor.execute("DELETE FROM user_sessions WHERE ip_address = ? AND user_id = ? AND CONVERT(NVARCHAR(255), session_token) != CONVERT(NVARCHAR(255), ?)", (ip_addr, user_id, current_session_token))
            else:
                cursor.execute("DELETE FROM user_sessions WHERE id = ? AND user_id = ?", (session_id, user_id))
                
            conn.commit()
            conn.close()
            return jsonify({'success': True, 'message': 'Oturum sonlandirildi'})
            
        # Eger ID bulunamazsa, token olarak aramayi deneyelim
        cursor.execute("SELECT CONVERT(NVARCHAR(255), session_token) FROM user_sessions WHERE CONVERT(NVARCHAR(255), session_token) = CONVERT(NVARCHAR(255), ?) AND user_id = ?", (str(session_id), user_id))
        row = cursor.fetchone()
        if row:
            if str(session_id) == current_session_token:
                conn.close()
                return jsonify({'success': False, 'error': 'Mevcut oturumunuzu buradan silemezsiniz, sistemden çıkış yapın.'}), 400
            cursor.execute("DELETE FROM user_sessions WHERE CONVERT(NVARCHAR(255), session_token) = CONVERT(NVARCHAR(255), ?) AND user_id = ?", (str(session_id), user_id))
            conn.commit()
            conn.close()
            return jsonify({'success': True, 'message': 'Oturum sonlandırıldı'})
            
        conn.close()
        return jsonify({'success': False, 'error': 'Oturum bulunamadı'}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@user_manager_bp.route('/sessions/<session_token>', methods=['DELETE'])
@require_auth
def delete_session(session_token):
    try:
        user_id = request.current_user.get('user_id')
        current_session_token = request.current_user.get('session_token')
        
        if session_token == current_session_token:
            return jsonify({'success': False, 'error': 'Mevcut oturumunuzu buradan silemezsiniz, sistemden çıkış yapın.'}), 400
            
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM user_sessions WHERE user_id = ? AND CONVERT(NVARCHAR(255), session_token) = CONVERT(NVARCHAR(255), ?)", (user_id, session_token))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Oturum sonlandırıldı'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
