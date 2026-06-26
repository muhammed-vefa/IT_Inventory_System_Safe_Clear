"""
JWT Kimlik Doğrulama Modülü – IT Envanter Sistemi
Her API isteğini doğrulayan güvenlik katmanıdır.
"""
import jwt
import os
import datetime
from functools import wraps
from flask import request, jsonify

JWT_SECRET = os.getenv("JWT_SECRET") or os.getenv("SECRET_KEY") or "SUPER_SECRET_KEY_123"
TOKEN_EXPIRY_HOURS = 12

def create_token(user_data, expiry_hours=None, session_token=None):
    """Giriş yapan kullanıcıya kısa süreli (15dk) access token keser."""
    hours = expiry_hours if expiry_hours is not None else TOKEN_EXPIRY_HOURS
    payload = {
        'user_id': user_data['id'],
        'username': user_data['username'],
        'display_name': user_data.get('display_name', ''),
        'role': user_data.get('role', 'VIEWER'),
        'permissions': user_data.get('permissions', []),
        'session_token': session_token,
        'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=hours),
        'iat': datetime.datetime.now(datetime.timezone.utc)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')

def create_refresh_token(user_id, client_ip=None, user_agent=None, expiry_days=7):
    """Uzun süreli (7 gün) refresh token keser."""
    import secrets
    token = secrets.token_urlsafe(64)
    expires_at = datetime.datetime.now() + datetime.timedelta(days=expiry_days)
    
    from core.database_sql import get_db_connection
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO refresh_tokens (user_id, token, expires_at, client_ip, user_agent) VALUES (?, ?, ?, ?, ?)",
        (user_id, token, expires_at, client_ip, user_agent)
    )
    conn.commit()
    conn.close()
    return token

# Alias for compatibility
generate_token = create_token

def decode_token(token):
    """Token'ı özümler, geçersizse None döner."""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
    except Exception as e:
        import logging
        logging.error(f"Token decode error: {e}")
        return None

def require_auth(f):
    """Endpoint'leri koruyan decorator – token zorunlu."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.method == 'OPTIONS':
            return jsonify({'status': 'ok'}), 200
            
        token = None
        auth_header = request.headers.get('Authorization')
        
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
        
        # Fallback to cookie
        if not token:
            token = request.cookies.get('access_token')

        if not token:
            return jsonify({'error': 'Oturum bulunamadı, giriş yapın'}), 401

        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
            
            # Tekli oturum kontrolü (Session Token eşleşmesi)
            token_session = payload.get('session_token')
            user_id = payload.get('user_id')
            
            if user_id:
                from core.database_sql import get_db_connection
                conn = get_db_connection()
                if conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT id FROM user_sessions WHERE user_id = ? AND CONVERT(NVARCHAR(255), session_token) = CONVERT(NVARCHAR(255), ?)", (user_id, token_session))
                    rows = cursor.fetchall()
                    db_row = rows[0] if rows else None
                    
                    # Son aktiviteyi güncelle
                    if db_row:
                        cursor.execute("UPDATE user_sessions SET last_activity = GETDATE() WHERE id = ?", (db_row[0],))
                        conn.commit()
                        
                    cursor.close()
                    conn.close()
                    
                    # Eğer session_token ile eşleşen bir oturum kaydı bulunamadıysa (uzaktan silinmişse veya başka giriş onu silmişse)
                    if token_session and not db_row:
                        return jsonify({'error': 'Oturumunuz geçerliliğini yitirdi veya uzaktan sonlandırıldı.', 'session_invalidated': True}), 401
                        
            request.current_user = payload
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Oturum süresi doldu, tekrar giriş yapın'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Geçersiz oturum bilgisi'}), 401

        return f(*args, **kwargs)
    return decorated

def require_admin(f):
    """Sadece ADMIN rolüne izin veren decorator."""
    @wraps(f)
    @require_auth
    def decorated(*args, **kwargs):
        if request.current_user.get('role') != 'ADMIN':
            return jsonify({'error': 'Bu işlem için yönetici yetkisi gerekli'}), 403
        return f(*args, **kwargs)
    return decorated

def require_editor(f):
    """Yetki kontrolü yapan decorator. ADMIN, EDITOR, DEPOT, VIEWER ve OTHER rollerini yönetir."""
    @wraps(f)
    @require_auth
    def decorated(*args, **kwargs):
        role = str(request.current_user.get('role', 'VIEWER') or 'VIEWER').upper()
        
        # ADMIN her şeyi yapabilir
        if role == 'ADMIN':
            return f(*args, **kwargs)
            
        # VIEWER hiçbir değiştirme/ekleme işlemi yapamaz
        if role == 'VIEWER':
            return jsonify({'error': 'İzleyici (Viewer) yetkisiyle bu işlem yapılamaz'}), 403
            
        # Modülü path'ten tespit et
        path = request.path
        module = 'dashboard'
        if '/inventory/' in path or '/pcs/' in path or '/monitors/' in path or '/tablets/' in path or '/areas/' in path: 
            module = 'inventory' # Veya 'areas' kendi başına olabilir ama genel olarak inventory
        if '/notes/' in path: module = 'general-notes'
        if '/areas/' in path: module = 'areas'
        if '/printers/' in path or '/cups/' in path: module = 'printers'
        if '/depot/' in path: module = 'depot'
        if '/document/' in path: module = 'docs'
        if '/service/' in path: module = 'service'
        if '/users/' in path or '/logs/' in path: module = 'admin_only'

        if role == 'EDITOR':
            if module == 'admin_only':
                return jsonify({'error': 'Bu işlem için ADMIN yetkisi gerekli'}), 403
            return f(*args, **kwargs)
            
        if role in ('DEPOT', 'DEPO', 'DEPOCU', 'WAREHOUSE'):
            if module == 'depot' or module == 'printers' or module == 'service':
                return f(*args, **kwargs)
            return jsonify({'error': 'Sadece Depo, Yazıcılar ve Yazıcı Servis işlemlerinde işlem yapabilirsiniz'}), 403
            
        if role == 'OTHER':
            import json
            perms_str = request.current_user.get('permissions', '[]')
            try: 
                perms = json.loads(perms_str)
            except: 
                perms = []
                
            if module in perms:
                return f(*args, **kwargs)
            return jsonify({'error': f'Bu işlem ({module}) için özel yetkiniz bulunmuyor'}), 403
            
        return jsonify({'error': 'Yetkilendirme hatası'}), 403
    return decorated

def require_depot_editor(f):
    """require_editor artık depo ve diğer rollerini dinamik yönettiği için alias olarak kullanıyoruz."""
    return require_editor(f)
