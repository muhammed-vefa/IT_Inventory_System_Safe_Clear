from flask import Blueprint, jsonify, request
from core.database_sql import get_db_connection, query_db
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
def get_kb_by_category(category):
    try:
        table = get_kb_table(category)
        results = query_db(f"SELECT * FROM {table} ORDER BY title ASC")
        return jsonify(results or [])
    except Exception as e:
        print(f"[KB GET] {category}: {e}")
        return jsonify([]), 500


# =====================================================
#  BILGI BANKASI: EKLEME
# =====================================================
@notes_manager_bp.route('/kb/add', methods=['POST'])
def add_kb():
    try:
        data = request.form if request.form else request.json
        title = data.get('title')
        content = data.get('content')
        category = data.get('type') or data.get('category') or 'kodlar'
        requires_user = int(data.get('requires_user', 0))
        user_name = data.get('user_name', 'Sistem')
        
        image_path = handle_image_upload()

        if not title:
            return jsonify({"success": False, "error": "Baslik zorunludur"}), 400
        
        table = get_kb_table(category)
        query_db(
            f"INSERT INTO {table} (title, content, requires_user, user_name, image_path, created_at) VALUES (?,?,?,?,?,GETDATE())",
            (title, content, requires_user, user_name, image_path)
        )
        return jsonify({"success": True, "message": "Bilgi basariyla kaydedildi."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# =====================================================
#  BILGI BANKASI: GUNCELLEME
# =====================================================
@notes_manager_bp.route('/kb/update/<int:id>', methods=['POST', 'PUT'])
def update_kb(id):
    try:
        data = request.form if request.form else request.json
        title = data.get('title')
        content = data.get('content')
        category = data.get('type') or data.get('category') or 'kodlar'
        requires_user = int(data.get('requires_user', 0))
        
        image_path = handle_image_upload()
        table = get_kb_table(category)
        
        if image_path:
            query_db(
                f"UPDATE {table} SET title=?, content=?, requires_user=?, image_path=? WHERE id=?",
                (title, content, requires_user, image_path, id)
            )
        else:
            query_db(
                f"UPDATE {table} SET title=?, content=?, requires_user=? WHERE id=?",
                (title, content, requires_user, id)
            )
        return jsonify({"success": True, "message": "Bilgi guncellendi."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# =====================================================
#  BILGI BANKASI: SILME
# =====================================================
@notes_manager_bp.route('/kb/delete/<int:id>', methods=['DELETE'])
def delete_kb(id):
    try:
        category = request.args.get('category', 'kodlar')
        table = get_kb_table(category)
        query_db(f"DELETE FROM {table} WHERE id = ?", (id,))
        return jsonify({"success": True, "message": "Bilgi silindi."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# =====================================================
#  CIHAZ NOTU SAYILARI (pcs icin)
# =====================================================
@notes_manager_bp.route('/counts/pc', methods=['GET'])
def get_pc_counts():
    try:
        res = query_db("SELECT user_name as hostname, COUNT(*) as c FROM technical_notes WHERE user_name IS NOT NULL GROUP BY user_name")
        return jsonify({r['hostname']: r['c'] for r in res} if res else {})
    except Exception as e:
        return jsonify({}), 500
