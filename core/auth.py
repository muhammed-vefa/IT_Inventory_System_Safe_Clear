import jwt, datetime, os, functools
from flask import request, jsonify
SECRET_KEY = os.getenv('SECRET_KEY') or 'SUPER_SECRET_KEY_123'
def generate_token(user_id, role):
 payload = {
 'user_id': user_id,
 'role': role,
 'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=8)
 }
 return jwt.encode(payload, SECRET_KEY, algorithm='HS256')
def token_required(f):
 @functools.wraps(f)
 def decorated(*args, **kwargs):
 token = request.headers.get('Authorization')
 if not token:
 return jsonify({'error': 'Token eksik!'}), 401
 try:
 data = jwt.decode(token.replace('Bearer ', ''), SECRET_KEY, algorithms=['HS256'])
 request.user_id = data['user_id']
 request.user_role = data['role']
 except:
 return jsonify({'error': 'Token geersiz!'}), 401
 return f(*args, **kwargs)
 return decorated
