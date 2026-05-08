"""
JWT Kimlik Doğrulama Modülü — IT Envanter Sistemi
Her API isteğini doğrulayan güvenlik katmanı.
"""
import jwt
import os
import datetime
from functools import wraps
from flask import request, jsonify

JWT_SECRET = os.getenv("JWT_SECRET") or os.getenv("SECRET_KEY")
if not JWT_SECRET:
    import secrets
    JWT_SECRET = secrets.token_hex(32)
    print("UYARI: JWT_SECRET veya SECRET_KEY .env'de tanımlı değil. Geçici bir anahtar üretildi.")
TOKEN_EXPIRY_HOURS = 8

def create_token(user_data):
    """Giriş yapan kullanıcıya 8 saatlik JWT token keser."""
    payload = {
        'user_id': user_data['id'],
        'username': user_data['username'],
        'display_name': user_data.get('display_name', ''),
        'role': user_data.get('role', 'VIEWER'),
        'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=TOKEN_EXPIRY_HOURS),
        'iat': datetime.datetime.now(datetime.timezone.utc)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')

def decode_token(token):
    """Token'ı çözümler, geçersizse None döner."""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def require_auth(f):
    """Endpoint'leri koruyan decorator — token zorunlu."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization')
        
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]

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
