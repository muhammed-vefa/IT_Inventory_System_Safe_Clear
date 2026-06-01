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

def create_token(user_data):
    """Giriş yapan kullanıcıya kısa süreli (15dk) access token keser."""
    payload = {
        'user_id': user_data['id'],
        'username': user_data['username'],
        'display_name': user_data.get('display_name', ''),
        'role': user_data.get('role', 'VIEWER'),
        'permissions': user_data.get('permissions', []),
        'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=TOKEN_EXPIRY_HOURS),
        'iat': datetime.datetime.now(datetime.timezone.utc)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')

def create_refresh_token(user_id):
    """Uzun süreli (7 gün) refresh token keser."""
    import secrets
    token = secrets.token_urlsafe(64)
    expires_at = datetime.datetime.now() + datetime.timedelta(days=7)
    
    from core.database_sql import get_db_connection
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO refresh_tokens (user_id, token, expires_at) VALUES (?, ?, ?)",
        (user_id, token, expires_at)
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
    """ADMIN veya EDITOR rolüne izin veren decorator."""
    @wraps(f)
    @require_auth
    def decorated(*args, **kwargs):
        if request.current_user.get('role') not in ('ADMIN', 'EDITOR'):
            return jsonify({'error': 'Bu işlem için düzenleme yetkisi gerekli'}), 403
        return f(*args, **kwargs)
    return decorated
