from functools import wraps
from flask import request, jsonify

# Role hierarchy and operation mapping
ROLE_PERMISSIONS = {
    'ADMIN': ['*'], # All operations
    'EDITOR': [
        'update_device', 'add_device', 'update_printer', 'add_printer',
        'update_kb', 'add_kb', 'archive_single'
    ],
    'USER': [
        'read_inventory', 'read_printers', 'read_kb', 'read_logs'
    ]
}

import json
import os



def require_operation(operation_name):
    """Operation tabanlı yetki kontrolü yapan decorator (Safe Mode Destekli)."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):


            if not hasattr(request, 'current_user'):
                return jsonify({"error": "Authentication required"}), 401
            
            user_role = request.current_user.get('role', 'USER')
            allowed_ops = ROLE_PERMISSIONS.get(user_role, [])
            
            if '*' in allowed_ops or operation_name in allowed_ops:
                return f(*args, **kwargs)
            
            return jsonify({
                "error": "Unauthorized operation",
                "required_permission": operation_name,
                "user_role": user_role
            }), 403
        return decorated_function
    return decorator
