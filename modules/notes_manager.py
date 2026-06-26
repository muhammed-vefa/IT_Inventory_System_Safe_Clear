from flask import Blueprint, jsonify, request
from core.database_sql import get_db_connection, query_db
from core.auth import require_auth
import os
import uuid
import datetime

notes_manager_bp = Blueprint('notes_manager', __name__)

# =====================================================
#  TABLO ESLEME: KB Kategori -> SQL Tablo Adi
# =====================================================
KB_TABLE_MAP = {
    'kodlar': 'technical_notes',
    'kapanis': 'closure_notes',
    'sorun-giderme': 'troubleshooting_notes'
}

def get_kb_table(category):
    """Kategori adina gore SQL tablo adini doner."""
    return KB_TABLE_MAP.get(category, 'technical_notes')

def handle_image_upload():
    """Resim dosyasini isleme ve dosya adini doner."""
    if 'image' in request.files:
        f = request.files['image']
        if f.filename:
            ext = os.path.splitext(f.filename)[1]
            fname = f"{uuid.uuid4().hex}{ext}"
            upload_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads', 'notes')
            os.makedirs(upload_dir, exist_ok=True)
            f.save(os.path.join(upload_dir, fname))
            return fname
    return None


# =====================================================
#  BILGI BANKASI: KATEGORI BAZLI LISTELEME
# =====================================================
@notes_manager_bp.route('/kb/<category>', methods=['GET'])
@require_auth
def get_kb_by_category(category):
    try:
        user_id = request.current_user.get('user_id')
        role = request.current_user.get('role')
        table = get_kb_table(category)
        
        if role == 'ADMIN':
            results = query_db(f"SELECT * FROM {table} ORDER BY title ASC")
        else:
            results = query_db(f"SELECT * FROM {table} WHERE ISNULL(is_restricted, 0) = 0 OR allowed_users LIKE ? ORDER BY title ASC", (f'%,{user_id},%',))
            
        return jsonify(results or [])
    except Exception as e:
        print(f"[KB GET] {category}: {e}")
        return jsonify([]), 500


# =====================================================
#  BILGI BANKASI: EKLEME
# =====================================================
@notes_manager_bp.route('/kb/add', methods=['POST'])
@require_auth
def add_kb():
    try:
        data = request.form if request.form else request.json
        title = data.get('title')
        content = data.get('content')
        category = data.get('type') or data.get('category') or 'kodlar'
        
        role = request.current_user.get('role')
        if category == 'kodlar' and role != 'ADMIN':
            return jsonify({"success": False, "error": "Komutları sadece ADMIN yetkisine sahip kullanıcılar ekleyebilir."}), 403
            
        requires_user = int(data.get('requires_user', 0))
        user_name = data.get('user_name', 'Sistem')
        
        is_restricted = 1 if str(data.get('is_restricted', 'false')).lower() in ['true', '1'] else 0
        allowed_users_raw = data.get('allowed_users')
        
        allowed_users = ""
        if is_restricted and allowed_users_raw:
            if isinstance(allowed_users_raw, str):
                clean_list = [x.strip() for x in allowed_users_raw.split(',') if x.strip()]
                allowed_users = f",{','.join(clean_list)}," if clean_list else ""
            elif isinstance(allowed_users_raw, list):
                allowed_users = f",{','.join(str(x) for x in allowed_users_raw)},"
        
        image_path = handle_image_upload()

        if not title:
            return jsonify({"success": False, "error": "Baslik zorunludur"}), 400
        
        table = get_kb_table(category)
        query_db(
            f"INSERT INTO {table} (title, content, requires_user, user_name, image_path, is_restricted, allowed_users, created_at) VALUES (?,?,?,?,?,?,?,GETDATE())",
            (title, content, requires_user, user_name, image_path, is_restricted, allowed_users)
        )
        return jsonify({"success": True, "message": "Bilgi basariyla kaydedildi."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# =====================================================
#  BILGI BANKASI: GUNCELLEME
# =====================================================
@notes_manager_bp.route('/kb/update/<int:id>', methods=['POST', 'PUT'])
@require_auth
def update_kb(id):
    try:
        data = request.form if request.form else request.json
        title = data.get('title')
        content = data.get('content')
        category = data.get('type') or data.get('category') or 'kodlar'
        original_category = data.get('original_type') or 'kodlar'
        
        role = request.current_user.get('role')
        if category == 'kodlar' and role != 'ADMIN':
            return jsonify({"success": False, "error": "Komutları sadece ADMIN yetkisine sahip kullanıcılar düzenleyebilir."}), 403
            
        requires_user = int(data.get('requires_user', 0))
        
        is_restricted = 1 if str(data.get('is_restricted', 'false')).lower() in ['true', '1'] else 0
        allowed_users_raw = data.get('allowed_users')
        
        allowed_users = ""
        if is_restricted and allowed_users_raw:
            if isinstance(allowed_users_raw, str):
                clean_list = [x.strip() for x in allowed_users_raw.split(',') if x.strip()]
                allowed_users = f",{','.join(clean_list)}," if clean_list else ""
            elif isinstance(allowed_users_raw, list):
                allowed_users = f",{','.join(str(x) for x in allowed_users_raw)},"
                
        image_path = handle_image_upload()
        table = get_kb_table(category)
        old_table = get_kb_table(original_category)
        
        editor_name = request.current_user.get('display_name') or request.current_user.get('username')
        
        if table != old_table:
            # Tablo (kategori) degisti. Eski tablodan okuyup silecegiz, yeni tabloya INSERT edecegiz.
            old_record = query_db(f"SELECT * FROM {old_table} WHERE id=?", (id,), one=True)
            if old_record:
                # Eger yeni bir resim yuklenmediyse eski resmi koru
                final_image = image_path if image_path else old_record.get('image_path')
                user_name = old_record.get('user_name', editor_name)
                
                query_db(
                    f"INSERT INTO {table} (title, content, requires_user, user_name, image_path, is_restricted, allowed_users, created_at, last_edit_user) VALUES (?,?,?,?,?,?,?,GETDATE(),?)",
                    (title, content, requires_user, user_name, final_image, is_restricted, allowed_users, editor_name)
                )
                query_db(f"DELETE FROM {old_table} WHERE id=?", (id,))
        else:
            # Tablo ayni, normal UPDATE
            if image_path:
                query_db(
                    f"UPDATE {table} SET title=?, content=?, requires_user=?, image_path=?, is_restricted=?, allowed_users=?, last_edit_user=? WHERE id=?",
                    (title, content, requires_user, image_path, is_restricted, allowed_users, editor_name, id)
                )
            else:
                query_db(
                    f"UPDATE {table} SET title=?, content=?, requires_user=?, is_restricted=?, allowed_users=?, last_edit_user=? WHERE id=?",
                    (title, content, requires_user, is_restricted, allowed_users, editor_name, id)
                )
        return jsonify({"success": True, "message": "Bilgi guncellendi."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# =====================================================
#  BILGI BANKASI: SILME
# =====================================================
@notes_manager_bp.route('/kb/delete/<int:id>', methods=['DELETE'])
@require_auth
def delete_kb(id):
    try:
        category = request.args.get('category', 'kodlar')
        
        role = request.current_user.get('role')
        if category == 'kodlar' and role != 'ADMIN':
            return jsonify({"success": False, "error": "Komutları sadece ADMIN yetkisine sahip kullanıcılar silebilir."}), 403
            
        table = get_kb_table(category)
        query_db(f"DELETE FROM {table} WHERE id = ?", (id,))
        return jsonify({"success": True, "message": "Bilgi silindi."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# =====================================================
#  CIHAZ NOTU SAYILARI (pcs icin)
# =====================================================
@notes_manager_bp.route('/counts/pc', methods=['GET'])
@require_auth
def get_pc_counts():
    try:
        res = query_db("SELECT user_name as hostname, COUNT(*) as c FROM technical_notes WHERE user_name IS NOT NULL GROUP BY user_name")
        return jsonify({r['hostname']: r['c'] for r in res} if res else {})
    except Exception as e:
        return jsonify({}), 500
